from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from smartread_api.chapter_summaries import DEFAULT_OPENAI_MODEL


class ChapterQuizGenerator(Protocol):
    provider: str
    model: str

    def generate_quiz(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
        core_concepts: list[dict[str, object]],
    ) -> dict[str, object]:
        pass


class ChapterQuizGenerationError(Exception):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class ChapterQuizValidationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class QuizCitationModel(BaseModel):
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


class QuizQuestionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    question_text: str = Field(min_length=1)
    question_type: str = Field(pattern="^(multiple_choice|true_false|scenario_application)$")
    answer_options: list[str] = Field(min_length=2)
    correct_answer: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    tested_concept: str = Field(min_length=1)
    citation_id: str = Field(min_length=1)

    @field_validator(
        "id",
        "question_text",
        "question_type",
        "correct_answer",
        "explanation",
        "tested_concept",
        "citation_id",
    )
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be blank")
        return stripped

    @field_validator("answer_options")
    @classmethod
    def strip_answer_options(cls, value: list[str]) -> list[str]:
        options = [option.strip() for option in value if option.strip()]
        if len(options) < 2:
            raise ValueError("objective questions need answer options")
        return options


class ChapterQuizModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[QuizQuestionModel] = Field(min_length=5, max_length=5)
    citations: list[QuizCitationModel] = Field(min_length=1)


class OpenAIChapterQuizGenerator:
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
    def from_env(cls) -> OpenAIChapterQuizGenerator:
        return cls()

    def generate_quiz(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
        core_concepts: list[dict[str, object]],
    ) -> dict[str, object]:
        if not self.api_key:
            raise ChapterQuizGenerationError(
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
                    "input": _build_openai_input(
                        chapter=chapter,
                        pages=pages,
                        core_concepts=core_concepts,
                    ),
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "smartread_chapter_quiz",
                            "strict": True,
                            "schema": ChapterQuizModel.model_json_schema(),
                        }
                    },
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ChapterQuizGenerationError(
                "OpenAI quiz generation failed. Retry this chapter."
            ) from error

        try:
            return json.loads(_extract_response_text(response.json()))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ChapterQuizGenerationError(
                "OpenAI returned an unreadable quiz. Retry this chapter."
            ) from error


AMBIGUOUS_ANSWERS = {
    "all of the above",
    "both",
    "it depends",
    "maybe",
    "none of the above",
}

TRIVIA_PATTERNS = (
    "how many times",
    "on what page",
    "page number",
    "which sentence",
    "what word",
)

STOPWORDS = {
    "about",
    "after",
    "also",
    "because",
    "before",
    "chapter",
    "during",
    "from",
    "into",
    "that",
    "their",
    "this",
    "through",
    "what",
    "when",
    "which",
    "with",
}


def validate_quiz_output(
    output: dict[str, object],
    *,
    pages: list[dict[str, object]],
    core_concepts: list[dict[str, object]],
) -> dict[str, object]:
    try:
        quiz = ChapterQuizModel.model_validate(output)
    except ValidationError as error:
        raise ChapterQuizValidationError("Quiz output must match the structured schema.") from error

    payload = quiz.model_dump()
    citations = _validate_citations(payload["citations"], pages=pages)
    citations_by_id = {citation["id"]: citation for citation in citations}
    concept_names = {_normalize_label(str(concept["name"])) for concept in core_concepts}
    if not concept_names:
        raise ChapterQuizValidationError("Quiz questions must link to generated Core Concepts.")

    _validate_question_quality(
        payload["questions"],
        citations_by_id=citations_by_id,
        concept_names=concept_names,
    )
    return {
        "questions": payload["questions"],
        "citations": citations,
    }


def _build_openai_instructions() -> str:
    return (
        "You are SmartRead, a private cited-learning system for nonfiction chapters. "
        "Generate exactly five objective quiz questions. Use only the accepted source pages. "
        "Each question must test understanding or application of one provided Core Concept, "
        "have one clear correct answer, avoid trivia, and cite a supporting source excerpt."
    )


def _build_openai_input(
    *,
    chapter: dict[str, object],
    pages: list[dict[str, object]],
    core_concepts: list[dict[str, object]],
) -> str:
    source_pages = "\n\n".join(
        (
            f"Source location: {page['source_location']}\n"
            f"Page number: {page['page_number']}\n"
            f"Text:\n{page['extracted_text']}"
        )
        for page in pages
    )
    concepts = "\n".join(f"- {concept['name']}" for concept in core_concepts)
    return (
        f"Chapter: {chapter['chapter_number']}. {chapter['title']}\n"
        f"Accepted pages: {chapter['start_page']}-{chapter['end_page']}\n\n"
        f"Core Concepts:\n{concepts}\n\n"
        "Generate exactly five grounded quiz questions.\n\n"
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
            raise ChapterQuizValidationError("Citation ids must be unique.")
        if source_location not in pages_by_location:
            raise ChapterQuizValidationError(
                "Quiz citations must point to stored pages inside the accepted chapter."
            )
        page = pages_by_location[source_location]
        if page_number != page["page_number"]:
            raise ChapterQuizValidationError("Citation page numbers must match source locations.")
        if _normalize_text(source_excerpt) not in _normalize_text(str(page["extracted_text"])):
            raise ChapterQuizValidationError(
                "Quiz source excerpts must come from the cited page."
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


def _validate_question_quality(
    questions: list[dict[str, object]],
    *,
    citations_by_id: dict[str, dict[str, object]],
    concept_names: set[str],
) -> None:
    seen_text: set[str] = set()
    for question in questions:
        normalized_text = _normalize_label(str(question["question_text"]))
        if normalized_text in seen_text:
            raise ChapterQuizValidationError("Quiz questions must not be duplicated.")
        seen_text.add(normalized_text)

        if any(pattern in normalized_text for pattern in TRIVIA_PATTERNS):
            raise ChapterQuizValidationError("Quiz questions must test understanding, not trivia.")

        _validate_answer_clarity(question)
        if _normalize_label(str(question["tested_concept"])) not in concept_names:
            raise ChapterQuizValidationError("Each quiz question must link to one Core Concept.")

        citation = citations_by_id.get(str(question["citation_id"]))
        if citation is None:
            raise ChapterQuizValidationError("Quiz question citations must reference real citations.")
        _validate_supported_question(question, citation)


def _validate_answer_clarity(question: dict[str, object]) -> None:
    options = [str(option) for option in question["answer_options"]]
    normalized_options = [_normalize_label(option) for option in options]
    if len(normalized_options) != len(set(normalized_options)):
        raise ChapterQuizValidationError("Quiz answer options must be distinct.")

    correct_answer = str(question["correct_answer"])
    normalized_correct = _normalize_label(correct_answer)
    if normalized_correct in AMBIGUOUS_ANSWERS:
        raise ChapterQuizValidationError("Quiz questions need one clear correct answer.")
    if normalized_options.count(normalized_correct) != 1:
        raise ChapterQuizValidationError("Quiz questions need one clear correct answer.")

    if question["question_type"] == "true_false" and set(normalized_options) != {"true", "false"}:
        raise ChapterQuizValidationError("True-or-false questions must use True and False options.")


def _validate_supported_question(
    question: dict[str, object],
    citation: dict[str, object],
) -> None:
    claim = " ".join(
        [
            str(question["question_text"]),
            str(question["explanation"]),
            str(question["tested_concept"]),
        ]
    )
    if not _excerpt_supports_claim(claim, str(citation["source_excerpt"])):
        raise ChapterQuizValidationError("Source excerpts must support quiz questions.")


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
