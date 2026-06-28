from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class UploadResult:
    success: bool
    message: str
    book: dict[str, Any] | None = None
    retryable: bool = False


@dataclass(frozen=True)
class BookListResult:
    success: bool
    books: list[dict[str, Any]]
    message: str = ""


@dataclass(frozen=True)
class ExtractionResult:
    success: bool
    message: str
    summary: dict[str, int]
    book: dict[str, Any] | None = None
    pages: list[dict[str, Any]] | None = None
    retryable: bool = False


@dataclass(frozen=True)
class ChapterDetectionResult:
    success: bool
    message: str
    summary: dict[str, Any]
    chapters: list[dict[str, Any]]
    book: dict[str, Any] | None = None
    retryable: bool = False


@dataclass(frozen=True)
class ChapterBoundaryReviewResult:
    success: bool
    message: str
    chapters: list[dict[str, Any]]
    book: dict[str, Any] | None = None
    retryable: bool = False


@dataclass(frozen=True)
class ChapterBoundaryListResult:
    success: bool
    chapters: list[dict[str, Any]]
    message: str = ""
    retryable: bool = False


@dataclass(frozen=True)
class ChapterSummaryResult:
    success: bool
    message: str
    summary: dict[str, Any] | None = None
    chapter: dict[str, Any] | None = None
    generation_status: str | None = None
    retryable: bool = False


@dataclass(frozen=True)
class ConceptsTakeawaysResult:
    success: bool
    message: str
    content: dict[str, Any] | None = None
    chapter: dict[str, Any] | None = None
    generation_status: str | None = None
    retryable: bool = False


@dataclass(frozen=True)
class QuizResult:
    success: bool
    message: str
    quiz: dict[str, Any] | None = None
    chapter: dict[str, Any] | None = None
    generation_status: str | None = None
    retryable: bool = False


@dataclass(frozen=True)
class QuizAnswerResult:
    success: bool
    message: str
    question_id: str
    selected_answer: str | None = None
    is_correct: bool | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    tested_concept: str | None = None
    citation_id: str | None = None
    source_location: str | None = None
    page_number: int | None = None
    source_excerpt: str | None = None
    progress: dict[str, int] | None = None
    missed_concept_status: str | None = None
    retryable: bool = False


@dataclass(frozen=True)
class QuizProgressResult:
    success: bool
    message: str
    progress: dict[str, int]
    answers: list[dict[str, Any]]
    retryable: bool = False


@dataclass(frozen=True)
class MissedConceptsResult:
    success: bool
    message: str
    summary: dict[str, int]
    missed_concepts: list[dict[str, Any]]
    retryable: bool = False


@dataclass(frozen=True)
class CitationEvidenceResult:
    success: bool
    message: str
    citation_id: str
    verification_status: str = "unverified"
    source_location: str | None = None
    page_number: int | None = None
    source_excerpt: str | None = None
    retryable: bool = False


def get_uploaded_books(
    api_base_url: str,
    *,
    client: httpx.Client | None = None,
) -> BookListResult:
    http_client = client or httpx.Client(timeout=5.0)
    try:
        response = http_client.get(f"{api_base_url.rstrip('/')}/books")
        response.raise_for_status()
        return BookListResult(success=True, books=response.json()["books"])
    except httpx.HTTPError:
        return BookListResult(
            success=False,
            books=[],
            message="Uploaded books could not be loaded. Refresh after FastAPI is available.",
        )


def extract_pdf_text_from_api(
    api_base_url: str,
    *,
    book_id: int,
    client: httpx.Client | None = None,
) -> ExtractionResult:
    http_client = client or httpx.Client(timeout=20.0)
    try:
        response = http_client.post(f"{api_base_url.rstrip('/')}/books/{book_id}/extraction")
        if response.status_code == 200:
            payload = response.json()
            summary = payload["summary"]
            return ExtractionResult(
                success=True,
                message=_format_extraction_summary(summary),
                summary=summary,
                book=payload["book"],
                pages=payload["pages"],
            )

        detail = response.json().get("detail", {})
        if isinstance(detail, dict):
            return ExtractionResult(
                success=False,
                message=detail.get("message", "Extraction failed. Retry with this PDF."),
                summary={},
                book=detail.get("book"),
                retryable=bool(detail.get("retryable", True)),
            )
        if isinstance(detail, str):
            return ExtractionResult(success=False, message=detail, summary={}, retryable=True)

        return ExtractionResult(
            success=False,
            message="Extraction failed. Retry with this PDF.",
            summary={},
            retryable=True,
        )
    except httpx.HTTPError:
        return ExtractionResult(
            success=False,
            message="Extraction failed. Check the FastAPI backend, then try again.",
            summary={},
            retryable=True,
        )


def detect_chapters_from_api(
    api_base_url: str,
    *,
    book_id: int,
    client: httpx.Client | None = None,
) -> ChapterDetectionResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.post(f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-detection")
        if response.status_code == 200:
            payload = response.json()
            summary = payload["summary"]
            chapters = payload["chapters"]
            return ChapterDetectionResult(
                success=True,
                message=_format_chapter_detection_summary(summary),
                summary=summary,
                chapters=chapters,
                book=payload["book"],
            )

        detail = response.json().get("detail", {})
        if isinstance(detail, str):
            return ChapterDetectionResult(
                success=False,
                message=detail,
                summary={},
                chapters=[],
                retryable=True,
            )

        return ChapterDetectionResult(
            success=False,
            message="Chapter detection failed. Retry after text extraction completes.",
            summary={},
            chapters=[],
            retryable=True,
        )
    except httpx.HTTPError:
        return ChapterDetectionResult(
            success=False,
            message="Chapter detection failed. Check the FastAPI backend, then try again.",
            summary={},
            chapters=[],
            retryable=True,
        )


def save_chapter_boundaries_to_api(
    api_base_url: str,
    *,
    book_id: int,
    chapters: list[dict[str, Any]],
    client: httpx.Client | None = None,
) -> ChapterBoundaryReviewResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.put(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries",
            json={"chapters": chapters},
        )
        if response.status_code == 200:
            payload = response.json()
            accepted_chapters = payload["chapters"]
            return ChapterBoundaryReviewResult(
                success=True,
                message=_format_boundary_review_summary(len(accepted_chapters)),
                chapters=accepted_chapters,
                book=payload["book"],
            )

        detail = response.json().get("detail", {})
        return ChapterBoundaryReviewResult(
            success=False,
            message=detail if isinstance(detail, str) else "Boundary review failed. Try again.",
            chapters=[],
            retryable=True,
        )
    except httpx.HTTPError:
        return ChapterBoundaryReviewResult(
            success=False,
            message="Boundary review failed. Check the FastAPI backend, then try again.",
            chapters=[],
            retryable=True,
        )


def get_chapter_boundaries_from_api(
    api_base_url: str,
    *,
    book_id: int,
    client: httpx.Client | None = None,
) -> ChapterBoundaryListResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.get(f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries")
        if response.status_code == 200:
            return ChapterBoundaryListResult(
                success=True,
                chapters=response.json()["chapters"],
            )

        detail = response.json().get("detail", {})
        return ChapterBoundaryListResult(
            success=False,
            chapters=[],
            message=detail if isinstance(detail, str) else "Accepted chapters could not be loaded.",
            retryable=True,
        )
    except httpx.HTTPError:
        return ChapterBoundaryListResult(
            success=False,
            chapters=[],
            message="Accepted chapters could not be loaded. Check FastAPI, then try again.",
            retryable=True,
        )


def generate_chapter_summary_from_api(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
    client: httpx.Client | None = None,
) -> ChapterSummaryResult:
    http_client = client or httpx.Client(timeout=60.0)
    try:
        response = http_client.post(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries/{chapter_number}/summary"
        )
        if response.status_code == 200:
            payload = response.json()
            chapter = payload["chapter"]
            return ChapterSummaryResult(
                success=True,
                message=_format_summary_generation_message(chapter),
                summary=payload["summary"],
                chapter=chapter,
                generation_status=payload["generation_status"],
            )

        detail = response.json().get("detail", {})
        if isinstance(detail, dict):
            failed_summary = detail.get("summary") or {}
            return ChapterSummaryResult(
                success=False,
                message=detail.get("message", "Summary generation failed. Retry this chapter."),
                summary=failed_summary.get("summary"),
                chapter=failed_summary.get("chapter"),
                generation_status=failed_summary.get("generation_status"),
                retryable=bool(detail.get("retryable", True)),
            )
        if isinstance(detail, str):
            return ChapterSummaryResult(success=False, message=detail, retryable=True)

        return ChapterSummaryResult(
            success=False,
            message="Summary generation failed. Retry this chapter.",
            retryable=True,
        )
    except httpx.HTTPError:
        return ChapterSummaryResult(
            success=False,
            message="Summary generation failed. Check the FastAPI backend, then try again.",
            retryable=True,
        )


def get_chapter_summary_from_api(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
    client: httpx.Client | None = None,
) -> ChapterSummaryResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.get(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries/{chapter_number}/summary"
        )
        if response.status_code == 200:
            payload = response.json()
            chapter = payload["chapter"]
            return ChapterSummaryResult(
                success=True,
                message=_format_summary_loaded_message(chapter),
                summary=payload["summary"],
                chapter=chapter,
                generation_status=payload["generation_status"],
            )

        detail = response.json().get("detail", {})
        return ChapterSummaryResult(
            success=False,
            message=detail if isinstance(detail, str) else "Summary could not be loaded.",
            retryable=response.status_code != 404,
        )
    except httpx.HTTPError:
        return ChapterSummaryResult(
            success=False,
            message="Summary could not be loaded. Check the FastAPI backend, then try again.",
            retryable=True,
        )


def generate_concepts_takeaways_from_api(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
    client: httpx.Client | None = None,
) -> ConceptsTakeawaysResult:
    http_client = client or httpx.Client(timeout=60.0)
    try:
        response = http_client.post(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries/"
            f"{chapter_number}/concepts-takeaways"
        )
        if response.status_code == 200:
            payload = response.json()
            chapter = payload["chapter"]
            return ConceptsTakeawaysResult(
                success=True,
                message=_format_concepts_generation_message(chapter),
                content=payload["content"],
                chapter=chapter,
                generation_status=payload["generation_status"],
            )

        detail = response.json().get("detail", {})
        if isinstance(detail, dict):
            failed = detail.get("concepts_takeaways") or {}
            return ConceptsTakeawaysResult(
                success=False,
                message=detail.get(
                    "message",
                    "Core Concepts and Key Takeaways generation failed. Retry this chapter.",
                ),
                content=failed.get("content"),
                chapter=failed.get("chapter"),
                generation_status=failed.get("generation_status"),
                retryable=bool(detail.get("retryable", True)),
            )
        if isinstance(detail, str):
            return ConceptsTakeawaysResult(success=False, message=detail, retryable=True)

        return ConceptsTakeawaysResult(
            success=False,
            message="Core Concepts and Key Takeaways generation failed. Retry this chapter.",
            retryable=True,
        )
    except httpx.HTTPError:
        return ConceptsTakeawaysResult(
            success=False,
            message=(
                "Core Concepts and Key Takeaways generation failed. "
                "Check the FastAPI backend, then try again."
            ),
            retryable=True,
        )


def get_concepts_takeaways_from_api(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
    client: httpx.Client | None = None,
) -> ConceptsTakeawaysResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.get(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries/"
            f"{chapter_number}/concepts-takeaways"
        )
        if response.status_code == 200:
            payload = response.json()
            chapter = payload["chapter"]
            return ConceptsTakeawaysResult(
                success=True,
                message=_format_concepts_loaded_message(chapter),
                content=payload["content"],
                chapter=chapter,
                generation_status=payload["generation_status"],
            )

        detail = response.json().get("detail", {})
        return ConceptsTakeawaysResult(
            success=False,
            message=detail if isinstance(detail, str) else "Concepts and takeaways could not be loaded.",
            retryable=response.status_code != 404,
        )
    except httpx.HTTPError:
        return ConceptsTakeawaysResult(
            success=False,
            message=(
                "Concepts and takeaways could not be loaded. "
                "Check the FastAPI backend, then try again."
            ),
            retryable=True,
        )


def generate_quiz_from_api(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
    client: httpx.Client | None = None,
) -> QuizResult:
    http_client = client or httpx.Client(timeout=60.0)
    try:
        response = http_client.post(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries/"
            f"{chapter_number}/quiz"
        )
        if response.status_code == 200:
            payload = response.json()
            chapter = payload["chapter"]
            return QuizResult(
                success=True,
                message=_format_quiz_generation_message(chapter),
                quiz=payload["quiz"],
                chapter=chapter,
                generation_status=payload["generation_status"],
            )

        detail = response.json().get("detail", {})
        if isinstance(detail, dict):
            failed = detail.get("quiz") or {}
            return QuizResult(
                success=False,
                message=detail.get("message", "Quiz generation failed. Retry this chapter."),
                quiz=failed.get("quiz"),
                chapter=failed.get("chapter"),
                generation_status=failed.get("generation_status"),
                retryable=bool(detail.get("retryable", True)),
            )
        if isinstance(detail, str):
            return QuizResult(success=False, message=detail, retryable=True)

        return QuizResult(
            success=False,
            message="Quiz generation failed. Retry this chapter.",
            retryable=True,
        )
    except httpx.HTTPError:
        return QuizResult(
            success=False,
            message="Quiz generation failed. Check the FastAPI backend, then try again.",
            retryable=True,
        )


def get_quiz_from_api(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
    client: httpx.Client | None = None,
) -> QuizResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.get(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries/"
            f"{chapter_number}/quiz"
        )
        if response.status_code == 200:
            payload = response.json()
            chapter = payload["chapter"]
            return QuizResult(
                success=True,
                message=_format_quiz_loaded_message(chapter),
                quiz=payload["quiz"],
                chapter=chapter,
                generation_status=payload["generation_status"],
            )

        detail = response.json().get("detail", {})
        return QuizResult(
            success=False,
            message=detail if isinstance(detail, str) else "Quiz could not be loaded.",
            retryable=response.status_code != 404,
        )
    except httpx.HTTPError:
        return QuizResult(
            success=False,
            message="Quiz could not be loaded. Check the FastAPI backend, then try again.",
            retryable=True,
        )


def submit_quiz_answer_to_api(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
    question_id: str,
    selected_answer: str,
    client: httpx.Client | None = None,
) -> QuizAnswerResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.post(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries/"
            f"{chapter_number}/quiz/answers/{question_id}",
            json={"selected_answer": selected_answer},
        )
        if response.status_code == 200:
            payload = response.json()
            return QuizAnswerResult(
                success=True,
                message=_format_quiz_answer_feedback_message(payload),
                question_id=payload["question_id"],
                selected_answer=payload["selected_answer"],
                is_correct=payload["is_correct"],
                correct_answer=payload["correct_answer"],
                explanation=payload["explanation"],
                tested_concept=payload["tested_concept"],
                citation_id=payload["citation_id"],
                source_location=payload["source_location"],
                page_number=payload["page_number"],
                source_excerpt=payload["source_excerpt"],
                progress=payload["progress"],
            )

        detail = response.json().get("detail", {})
        return QuizAnswerResult(
            success=False,
            message=detail if isinstance(detail, str) else "Answer feedback failed. Try again.",
            question_id=question_id,
            retryable=response.status_code != 404,
        )
    except httpx.HTTPError:
        return QuizAnswerResult(
            success=False,
            message="Answer feedback failed. Check the FastAPI backend, then try again.",
            question_id=question_id,
            retryable=True,
        )


def get_quiz_progress_from_api(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
    client: httpx.Client | None = None,
) -> QuizProgressResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.get(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries/"
            f"{chapter_number}/quiz/progress"
        )
        if response.status_code == 200:
            payload = response.json()
            return QuizProgressResult(
                success=True,
                message="Quiz progress loaded.",
                progress=payload["progress"],
                answers=payload["answers"],
            )

        detail = response.json().get("detail", {})
        return QuizProgressResult(
            success=False,
            message=detail if isinstance(detail, str) else "Quiz progress could not be loaded.",
            progress={},
            answers=[],
            retryable=response.status_code != 404,
        )
    except httpx.HTTPError:
        return QuizProgressResult(
            success=False,
            message="Quiz progress could not be loaded. Check the FastAPI backend, then try again.",
            progress={},
            answers=[],
            retryable=True,
        )


def get_missed_concepts_from_api(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
    client: httpx.Client | None = None,
) -> MissedConceptsResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.get(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries/"
            f"{chapter_number}/missed-concepts"
        )
        if response.status_code == 200:
            payload = response.json()
            return MissedConceptsResult(
                success=True,
                message="Missed Concepts loaded.",
                summary=payload["summary"],
                missed_concepts=payload["missed_concepts"],
            )

        detail = response.json().get("detail", {})
        return MissedConceptsResult(
            success=False,
            message=detail if isinstance(detail, str) else "Missed Concepts could not be loaded.",
            summary={},
            missed_concepts=[],
            retryable=response.status_code != 404,
        )
    except httpx.HTTPError:
        return MissedConceptsResult(
            success=False,
            message="Missed Concepts could not be loaded. Check FastAPI, then try again.",
            summary={},
            missed_concepts=[],
            retryable=True,
        )


def retry_missed_question_to_api(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
    question_id: str,
    selected_answer: str,
    client: httpx.Client | None = None,
) -> QuizAnswerResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.post(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries/"
            f"{chapter_number}/missed-concepts/{question_id}/retry",
            json={"selected_answer": selected_answer},
        )
        if response.status_code == 200:
            payload = response.json()
            return QuizAnswerResult(
                success=True,
                message=_format_quiz_answer_feedback_message(payload),
                question_id=payload["question_id"],
                selected_answer=payload["selected_answer"],
                is_correct=payload["is_correct"],
                correct_answer=payload["correct_answer"],
                explanation=payload["explanation"],
                tested_concept=payload["tested_concept"],
                citation_id=payload["citation_id"],
                source_location=payload["source_location"],
                page_number=payload["page_number"],
                source_excerpt=payload["source_excerpt"],
                progress=payload["progress"],
                missed_concept_status=payload["missed_concept_status"],
            )

        detail = response.json().get("detail", {})
        return QuizAnswerResult(
            success=False,
            message=detail if isinstance(detail, str) else "Retry failed. Try again.",
            question_id=question_id,
            retryable=response.status_code != 404,
        )
    except httpx.HTTPError:
        return QuizAnswerResult(
            success=False,
            message="Retry failed. Check the FastAPI backend, then try again.",
            question_id=question_id,
            retryable=True,
        )


def get_citation_evidence_from_api(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
    citation_id: str,
    client: httpx.Client | None = None,
) -> CitationEvidenceResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.get(
            f"{api_base_url.rstrip('/')}/books/{book_id}/chapter-boundaries/"
            f"{chapter_number}/summary/citations/{citation_id}/evidence"
        )
        if response.status_code == 200:
            payload = response.json()
            return CitationEvidenceResult(
                success=True,
                message=payload["message"],
                citation_id=payload["citation_id"],
                verification_status=payload["verification_status"],
                source_location=payload["source_location"],
                page_number=payload["page_number"],
                source_excerpt=payload["source_excerpt"],
            )

        detail = response.json().get("detail", {})
        return CitationEvidenceResult(
            success=False,
            message=detail if isinstance(detail, str) else "Evidence could not be loaded.",
            citation_id=citation_id,
            retryable=response.status_code != 404,
        )
    except httpx.HTTPError:
        return CitationEvidenceResult(
            success=False,
            message="Evidence could not be loaded. Check the FastAPI backend, then try again.",
            citation_id=citation_id,
            retryable=True,
        )


def upload_pdf_to_api(
    api_base_url: str,
    *,
    filename: str,
    content: bytes,
    content_type: str,
    client: httpx.Client | None = None,
) -> UploadResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.post(
            f"{api_base_url.rstrip('/')}/books/uploads",
            files={"file": (filename, content, content_type)},
        )
        if response.status_code == 201:
            book = response.json()
            return UploadResult(
                success=True,
                message=f"{book['original_filename']} is ready in SmartRead.",
                book=book,
            )

        detail = response.json().get("detail", {})
        if isinstance(detail, dict):
            return UploadResult(
                success=False,
                message=detail.get("message", "Upload failed. Choose a PDF you own and try again."),
                retryable=bool(detail.get("retryable", True)),
                book=detail.get("book"),
            )
        if isinstance(detail, str):
            return UploadResult(success=False, message=detail, retryable=True)

        return UploadResult(
            success=False,
            message="Upload failed. Choose a PDF you own and try again.",
            retryable=True,
        )
    except httpx.HTTPError:
        return UploadResult(
            success=False,
            message="Upload failed. Check the FastAPI backend, then try again.",
            retryable=True,
        )


def _format_extraction_summary(summary: dict[str, int]) -> str:
    return (
        "Extraction complete: "
        f"{summary['page_count']} pages, "
        f"{summary['text_page_count']} with text, "
        f"{summary['blank_page_count']} blank."
    )


def _format_chapter_detection_summary(summary: dict[str, Any]) -> str:
    chapter_count = summary["chapter_count"]
    confidence = summary["confidence"]
    if chapter_count == 0:
        return "No chapters could be detected. Manual chapter review will be required."

    return f"Detected {chapter_count} chapters with {confidence} confidence."


def _format_boundary_review_summary(chapter_count: int) -> str:
    noun = "boundary" if chapter_count == 1 else "boundaries"
    return f"Accepted {chapter_count} reviewed chapter {noun}."


def _format_summary_generation_message(chapter: dict[str, Any]) -> str:
    return f"Summary generated for Chapter {chapter['chapter_number']}: {chapter['title']}."


def _format_summary_loaded_message(chapter: dict[str, Any]) -> str:
    return f"Summary loaded for Chapter {chapter['chapter_number']}: {chapter['title']}."


def _format_concepts_generation_message(chapter: dict[str, Any]) -> str:
    return (
        "Core Concepts and Key Takeaways generated for "
        f"Chapter {chapter['chapter_number']}: {chapter['title']}."
    )


def _format_concepts_loaded_message(chapter: dict[str, Any]) -> str:
    return (
        "Core Concepts and Key Takeaways loaded for "
        f"Chapter {chapter['chapter_number']}: {chapter['title']}."
    )


def _format_quiz_generation_message(chapter: dict[str, Any]) -> str:
    return f"Quiz generated for Chapter {chapter['chapter_number']}: {chapter['title']}."


def _format_quiz_loaded_message(chapter: dict[str, Any]) -> str:
    return f"Quiz loaded for Chapter {chapter['chapter_number']}: {chapter['title']}."


def _format_quiz_answer_feedback_message(payload: dict[str, Any]) -> str:
    return "Correct." if payload["is_correct"] else "Incorrect."
