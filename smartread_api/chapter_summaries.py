from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

import httpx


DEFAULT_OPENAI_MODEL = "gpt-5.5"


class ChapterSummaryGenerator(Protocol):
    provider: str
    model: str

    def generate_summary(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
    ) -> dict[str, object]:
        pass


class ChapterSummaryGenerationError(Exception):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class ChapterSummaryValidationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class OpenAIChapterSummaryGenerator:
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
    def from_env(cls) -> OpenAIChapterSummaryGenerator:
        return cls()

    def generate_summary(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
    ) -> dict[str, object]:
        if not self.api_key:
            raise ChapterSummaryGenerationError(
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
                            "name": "smartread_chapter_summary",
                            "strict": True,
                            "schema": SUMMARY_JSON_SCHEMA,
                        }
                    },
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ChapterSummaryGenerationError(
                "OpenAI summary generation failed. Retry generation for this chapter."
            ) from error

        try:
            return json.loads(_extract_response_text(response.json()))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ChapterSummaryGenerationError(
                "OpenAI returned an unreadable summary. Retry generation for this chapter."
            ) from error


SUMMARY_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["central_argument", "supporting_ideas", "citations"],
    "properties": {
        "central_argument": {
            "type": "object",
            "additionalProperties": False,
            "required": ["claim", "citation_ids"],
            "properties": {
                "claim": {"type": "string", "minLength": 1},
                "citation_ids": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "minLength": 1},
                },
            },
        },
        "supporting_ideas": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["claim", "citation_ids"],
                "properties": {
                    "claim": {"type": "string", "minLength": 1},
                    "citation_ids": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
        "citations": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "source_location", "page_number", "source_excerpt"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "source_location": {"type": "string", "minLength": 1},
                    "page_number": {"type": "integer", "minimum": 1},
                    "source_excerpt": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}


STOPWORDS = {
    "about",
    "after",
    "also",
    "argues",
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


def validate_chapter_summary_output(
    output: dict[str, object],
    *,
    pages: list[dict[str, object]],
) -> dict[str, object]:
    if not isinstance(output, dict):
        raise ChapterSummaryValidationError("Summary output must be a structured object.")
    _reject_unsupported_fields(
        output,
        {"central_argument", "supporting_ideas", "citations"},
        "Summary output contains unsupported fields.",
    )

    central_argument = _validate_claim_object(
        output.get("central_argument"),
        label="central_argument",
    )
    supporting_ideas = _validate_supporting_ideas(output.get("supporting_ideas"))
    citations = _validate_citations(output.get("citations"), pages=pages)
    citations_by_id = {citation["id"]: citation for citation in citations}

    _validate_claim_citations(central_argument, citations_by_id)
    for idea in supporting_ideas:
        _validate_claim_citations(idea, citations_by_id)

    return {
        "central_argument": central_argument,
        "supporting_ideas": supporting_ideas,
        "citations": citations,
    }


def _build_openai_instructions() -> str:
    return (
        "You are SmartRead, a private cited-learning system for nonfiction chapters. "
        "Generate only the requested JSON object. Use only the provided source pages. "
        "Every important claim must cite source excerpts from those pages."
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
        "Write a cited Summary with one central argument and important supporting ideas.\n\n"
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


def _validate_claim_object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ChapterSummaryValidationError(f"{label} must be a structured claim.")
    _reject_unsupported_fields(
        value,
        {"claim", "citation_ids"},
        f"{label} contains unsupported fields.",
    )

    claim = value.get("claim")
    citation_ids = value.get("citation_ids")
    if not isinstance(claim, str) or not claim.strip():
        raise ChapterSummaryValidationError(f"{label} needs a claim.")
    if not isinstance(citation_ids, list) or not citation_ids:
        raise ChapterSummaryValidationError(f"{label} needs at least one citation.")
    if not all(isinstance(citation_id, str) and citation_id.strip() for citation_id in citation_ids):
        raise ChapterSummaryValidationError(f"{label} citation references must be citation ids.")

    return {
        "claim": claim.strip(),
        "citation_ids": [citation_id.strip() for citation_id in citation_ids],
    }


def _validate_supporting_ideas(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ChapterSummaryValidationError("Summary needs at least one supporting idea.")

    return [
        _validate_claim_object(idea, label=f"supporting_ideas[{index}]")
        for index, idea in enumerate(value)
    ]


def _validate_citations(
    value: object,
    *,
    pages: list[dict[str, object]],
) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ChapterSummaryValidationError("Summary needs at least one citation.")

    pages_by_location = {page["source_location"]: page for page in pages}
    seen_ids: set[str] = set()
    citations = []
    for citation in value:
        if not isinstance(citation, dict):
            raise ChapterSummaryValidationError("Each citation must be structured.")
        _reject_unsupported_fields(
            citation,
            {"id", "source_location", "page_number", "source_excerpt"},
            "Citation output contains unsupported fields.",
        )

        citation_id = citation.get("id")
        source_location = citation.get("source_location")
        page_number = citation.get("page_number")
        source_excerpt = citation.get("source_excerpt")
        if not isinstance(citation_id, str) or not citation_id.strip():
            raise ChapterSummaryValidationError("Each citation needs an id.")
        if citation_id in seen_ids:
            raise ChapterSummaryValidationError("Citation ids must be unique.")
        if source_location not in pages_by_location:
            raise ChapterSummaryValidationError(
                "Citations must point to stored pages inside the accepted chapter."
            )
        page = pages_by_location[source_location]
        if page_number != page["page_number"]:
            raise ChapterSummaryValidationError("Citation page numbers must match source locations.")
        if not isinstance(source_excerpt, str) or not source_excerpt.strip():
            raise ChapterSummaryValidationError("Each citation needs a source excerpt.")
        if _normalize_text(source_excerpt) not in _normalize_text(str(page["extracted_text"])):
            raise ChapterSummaryValidationError(
                "Citation source excerpts must come from the cited page."
            )

        seen_ids.add(citation_id)
        citations.append(
            {
                "id": citation_id.strip(),
                "source_location": str(source_location),
                "page_number": int(page_number),
                "source_excerpt": source_excerpt.strip(),
            }
        )

    return citations


def _reject_unsupported_fields(
    value: dict[str, object],
    allowed_fields: set[str],
    message: str,
) -> None:
    if set(value) - allowed_fields:
        raise ChapterSummaryValidationError(message)


def _validate_claim_citations(
    claim_object: dict[str, object],
    citations_by_id: dict[str, dict[str, object]],
) -> None:
    claim = str(claim_object["claim"])
    for citation_id in claim_object["citation_ids"]:
        citation = citations_by_id.get(str(citation_id))
        if citation is None:
            raise ChapterSummaryValidationError("Claim citations must reference real citations.")
        if not _excerpt_supports_claim(claim, str(citation["source_excerpt"])):
            raise ChapterSummaryValidationError("Source excerpts must support cited claims.")


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
