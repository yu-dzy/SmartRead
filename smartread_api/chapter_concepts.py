from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from smartread_api.chapter_summaries import DEFAULT_OPENAI_MODEL


class ConceptsTakeawaysGenerator(Protocol):
    provider: str
    model: str

    def generate_concepts_takeaways(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
    ) -> dict[str, object]:
        pass


class ConceptsTakeawaysGenerationError(Exception):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class ConceptsTakeawaysValidationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class CitationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    source_excerpt: str = Field(min_length=1)

    @field_validator("id", "source_location", "source_excerpt")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be blank")
        return stripped


class CoreConceptModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    example: str | None = None
    citation_ids: list[str] = Field(min_length=1)

    @field_validator("name", "explanation", "why_it_matters")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be blank")
        return stripped

    @field_validator("example")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("citation_ids")
    @classmethod
    def strip_citation_ids(cls, value: list[str]) -> list[str]:
        citation_ids = [citation_id.strip() for citation_id in value if citation_id.strip()]
        if not citation_ids:
            raise ValueError("concepts need citations")
        return citation_ids


class KeyTakeawayModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    citation_ids: list[str] = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("takeaway cannot be blank")
        return stripped

    @field_validator("citation_ids")
    @classmethod
    def strip_citation_ids(cls, value: list[str]) -> list[str]:
        citation_ids = [citation_id.strip() for citation_id in value if citation_id.strip()]
        if not citation_ids:
            raise ValueError("takeaways need citations")
        return citation_ids


class ConceptsTakeawaysModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    core_concepts: list[CoreConceptModel] = Field(min_length=1)
    key_takeaways: list[KeyTakeawayModel] = Field(min_length=1)
    citations: list[CitationModel] = Field(min_length=1)


class OpenAIConceptsTakeawaysGenerator:
    provider = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: httpx.Client | None = None,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or os.environ.get("SMARTREAD_OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        self.client = client or httpx.Client(timeout=60.0)
        self.base_url = base_url.rstrip("/")

    @classmethod
    def from_env(cls) -> OpenAIConceptsTakeawaysGenerator:
        return cls()

    def generate_concepts_takeaways(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
    ) -> dict[str, object]:
        if not self.api_key:
            raise ConceptsTakeawaysGenerationError(
                "OpenAI generation is not configured. Set OPENAI_API_KEY and retry."
            )

        try:
            response = self.client.post(
                f"{self.base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "store": False,
                    "instructions": _build_openai_instructions(),
                    "input": _build_openai_input(chapter=chapter, pages=pages),
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "smartread_concepts_takeaways",
                            "strict": True,
                            "schema": ConceptsTakeawaysModel.model_json_schema(),
                        }
                    },
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ConceptsTakeawaysGenerationError(
                "OpenAI concepts and takeaways generation failed. Retry this chapter."
            ) from error

        try:
            return json.loads(_extract_response_text(response.json()))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ConceptsTakeawaysGenerationError(
                "OpenAI returned unreadable concepts and takeaways. Retry this chapter."
            ) from error


GENERIC_CONCEPT_NAMES = {
    "action",
    "business",
    "focus",
    "growth",
    "habits",
    "learning",
    "mindset",
    "motivation",
    "productivity",
    "success",
    "time management",
}

STOPWORDS = {
    "about",
    "after",
    "also",
    "because",
    "before",
    "chapter",
    "from",
    "into",
    "that",
    "their",
    "this",
    "through",
    "when",
    "with",
}


def validate_concepts_takeaways_output(
    output: dict[str, object],
    *,
    pages: list[dict[str, object]],
) -> dict[str, object]:
    try:
        content = ConceptsTakeawaysModel.model_validate(output)
    except ValidationError as error:
        raise ConceptsTakeawaysValidationError(
            "Concept and takeaway output must match the structured schema."
        ) from error

    payload = content.model_dump()
    _validate_concept_quality(payload["core_concepts"])
    citations = _validate_citations(payload["citations"], pages=pages)
    citations_by_id = {citation["id"]: citation for citation in citations}

    for concept in payload["core_concepts"]:
        _validate_citation_references(concept["citation_ids"], citations_by_id)
        _validate_supported_claim(
            " ".join(
                part
                for part in [
                    concept["name"],
                    concept["explanation"],
                    concept["why_it_matters"],
                    concept.get("example") or "",
                ]
                if part
            ),
            concept["citation_ids"],
            citations_by_id,
        )

    for takeaway in payload["key_takeaways"]:
        _validate_citation_references(takeaway["citation_ids"], citations_by_id)
        _validate_supported_claim(takeaway["text"], takeaway["citation_ids"], citations_by_id)

    return {
        "core_concepts": payload["core_concepts"],
        "key_takeaways": payload["key_takeaways"],
        "citations": citations,
    }


def _build_openai_instructions() -> str:
    return (
        "You are SmartRead, a private cited-learning system for nonfiction chapters. "
        "Generate only the requested JSON object. Use only the provided source pages. "
        "Core Concepts must be specific, useful, non-generic, and cited. Key Takeaways "
        "must be concise, chapter-specific, and cited."
    )


def _build_openai_input(
    *,
    chapter: dict[str, object],
    pages: list[dict[str, object]],
) -> str:
    source_pages = "\n\n".join(
        (
            f"Source location: {page['source_location']}\n"
            f"Page number: {page['page_number']}\n"
            f"Text:\n{page['extracted_text']}"
        )
        for page in pages
    )
    return (
        f"Chapter: {chapter['chapter_number']}. {chapter['title']}\n"
        f"Accepted pages: {chapter['start_page']}-{chapter['end_page']}\n\n"
        "Generate Core Concepts and Key Takeaways for this chapter.\n\n"
        f"{source_pages}"
    )


def _extract_response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]

    for output_item in payload.get("output", []):
        for content_item in output_item.get("content", []):
            text = content_item.get("text")
            if isinstance(text, str):
                return text

    raise KeyError("output_text")


def _validate_concept_quality(concepts: list[dict[str, object]]) -> None:
    seen_names: set[str] = set()
    for concept in concepts:
        normalized_name = _normalize_label(str(concept["name"]))
        if normalized_name in GENERIC_CONCEPT_NAMES:
            raise ConceptsTakeawaysValidationError("Core Concepts must be specific, not generic.")
        if normalized_name in seen_names:
            raise ConceptsTakeawaysValidationError("Core Concepts must not be duplicated.")
        seen_names.add(normalized_name)


def _validate_citations(
    value: list[dict[str, object]],
    *,
    pages: list[dict[str, object]],
) -> list[dict[str, object]]:
    pages_by_location = {page["source_location"]: page for page in pages}
    seen_ids: set[str] = set()
    citations = []
    for citation in value:
        citation_id = str(citation["id"])
        source_location = citation["source_location"]
        page_number = citation["page_number"]
        source_excerpt = str(citation["source_excerpt"])

        if citation_id in seen_ids:
            raise ConceptsTakeawaysValidationError("Citation ids must be unique.")
        if source_location not in pages_by_location:
            raise ConceptsTakeawaysValidationError(
                "Citations must point to stored pages inside the accepted chapter."
            )
        page = pages_by_location[source_location]
        if page_number != page["page_number"]:
            raise ConceptsTakeawaysValidationError(
                "Citation page numbers must match source locations."
            )
        if _normalize_text(source_excerpt) not in _normalize_text(str(page["extracted_text"])):
            raise ConceptsTakeawaysValidationError(
                "Citation source excerpts must come from the cited page."
            )

        seen_ids.add(citation_id)
        citations.append(
            {
                "id": citation_id,
                "source_location": str(source_location),
                "page_number": int(page_number),
                "source_excerpt": source_excerpt,
            }
        )

    return citations


def _validate_citation_references(
    citation_ids: list[str],
    citations_by_id: dict[str, dict[str, object]],
) -> None:
    for citation_id in citation_ids:
        if citation_id not in citations_by_id:
            raise ConceptsTakeawaysValidationError(
                "Concept and takeaway citations must reference real citations."
            )


def _validate_supported_claim(
    claim: str,
    citation_ids: list[str],
    citations_by_id: dict[str, dict[str, object]],
) -> None:
    for citation_id in citation_ids:
        citation = citations_by_id[citation_id]
        if not _excerpt_supports_claim(claim, str(citation["source_excerpt"])):
            raise ConceptsTakeawaysValidationError(
                "Source excerpts must support concept and takeaway claims."
            )


def _excerpt_supports_claim(claim: str, excerpt: str) -> bool:
    claim_terms = _meaningful_terms(claim)
    if not claim_terms:
        return True

    excerpt_terms = _meaningful_terms(excerpt)
    overlap_count = len(claim_terms.intersection(excerpt_terms))
    required_overlap = 1 if len(claim_terms) <= 3 else 2
    return overlap_count >= required_overlap


def _meaningful_terms(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z'-]{3,}", value.lower())
        if token not in STOPWORDS
    }


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).lower()


def _normalize_label(value: str) -> str:
    return " ".join(value.strip().lower().split())
