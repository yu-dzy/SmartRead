from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from smartread_frontend.health import ApiStatus
from smartread_frontend.uploads import (
    BookListResult,
    ChapterBoundaryListResult,
    ChapterBoundaryReviewResult,
    ChapterDetectionResult,
    ChapterSummaryResult,
    CitationEvidenceResult,
    ConceptsTakeawaysResult,
    ExtractionResult,
    MissedConceptsResult,
    QuizAnswerResult,
    QuizProgressResult,
    QuizResult,
    UploadResult,
)


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _empty_quiz_result(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
) -> QuizResult:
    return QuizResult(
        success=False,
        message="Quiz has not been generated yet.",
        retryable=False,
    )


def _empty_quiz_progress_result(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
) -> QuizProgressResult:
    return QuizProgressResult(
        success=True,
        message="Quiz progress loaded.",
        progress={
            "answered_count": 0,
            "correct_count": 0,
            "incorrect_count": 0,
            "total_questions": 5,
        },
        answers=[],
    )


def _empty_missed_concepts_result(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
) -> MissedConceptsResult:
    return MissedConceptsResult(
        success=True,
        message="Missed Concepts loaded.",
        summary={"missed_concept_count": 0},
        missed_concepts=[],
    )


@pytest.fixture(autouse=True)
def stub_missed_concepts_loader(monkeypatch):
    import smartread_frontend.uploads as uploads_module

    monkeypatch.setattr(
        uploads_module,
        "get_missed_concepts_from_api",
        _empty_missed_concepts_result,
        raising=False,
    )


def _empty_summary_result(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
) -> ChapterSummaryResult:
    return ChapterSummaryResult(
        success=False,
        message="Chapter Summary has not been generated yet.",
        retryable=False,
    )


def _empty_concepts_result(
    api_base_url: str,
    *,
    book_id: int,
    chapter_number: int,
) -> ConceptsTakeawaysResult:
    return ConceptsTakeawaysResult(
        success=False,
        message="Core Concepts and Key Takeaways have not been generated yet.",
        retryable=False,
    )


def _sample_quiz_content() -> dict[str, object]:
    return {
        "questions": [
            {
                "id": "q1",
                "question_text": "What does protected attention reduce?",
                "question_type": "multiple_choice",
                "answer_options": ["Constant switching", "Long-term memory"],
                "correct_answer": "Constant switching",
                "explanation": "Protected attention reduces constant switching.",
                "tested_concept": "Protected Attention",
                "citation_id": "qc1",
            },
            {
                "id": "q2",
                "question_text": "True or false: retrieval cues help recall.",
                "question_type": "true_false",
                "answer_options": ["True", "False"],
                "correct_answer": "True",
                "explanation": "Retrieval cues help learners recall ideas.",
                "tested_concept": "Retrieval Cues",
                "citation_id": "qc2",
            },
            {
                "id": "q3",
                "question_text": "Which concept applies when a learner silences chat?",
                "question_type": "scenario_application",
                "answer_options": ["Protected Attention", "Retrieval Cues"],
                "correct_answer": "Protected Attention",
                "explanation": "Silencing chat protects attention.",
                "tested_concept": "Protected Attention",
                "citation_id": "qc1",
            },
            {
                "id": "q4",
                "question_text": "Which practice connects ideas to memory?",
                "question_type": "multiple_choice",
                "answer_options": ["Retrieval cues", "Ignoring feedback"],
                "correct_answer": "Retrieval cues",
                "explanation": "Retrieval cues connect practice to memory.",
                "tested_concept": "Retrieval Cues",
                "citation_id": "qc2",
            },
            {
                "id": "q5",
                "question_text": "What makes deliberate practice easier to repeat?",
                "question_type": "multiple_choice",
                "answer_options": ["Reducing context switching", "Removing citations"],
                "correct_answer": "Reducing context switching",
                "explanation": "Protected blocks reduce context switching.",
                "tested_concept": "Protected Attention",
                "citation_id": "qc1",
            },
        ],
        "citations": [
            {
                "id": "qc1",
                "source_location": "book:20:page:1",
                "page_number": 1,
                "source_excerpt": "Protected attention reduces constant switching.",
            },
            {
                "id": "qc2",
                "source_location": "book:20:page:2",
                "page_number": 2,
                "source_excerpt": "Retrieval cues help learners recall ideas.",
            },
        ],
    }


def test_streamlit_uploads_pdf_and_shows_uploaded_book(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = []

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_upload_pdf_to_api(
        api_base_url: str,
        *,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> UploadResult:
        book = {
            "id": 1,
            "original_filename": filename,
            "content_type": content_type,
            "file_size": len(content),
            "uploaded_at": "2026-06-27T12:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "not_started",
            "error_message": None,
        }
        uploaded_books[:] = [book]
        return UploadResult(
            success=True,
            message=f"{filename} is ready in SmartRead.",
            book=book,
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(uploads_module, "upload_pdf_to_api", fake_upload_pdf_to_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Only upload books you own or have permission to use." in page_text
    assert len(app.file_uploader) == 1
    assert app.file_uploader[0].allowed_type == [".pdf"]

    app.file_uploader[0].set_value(("deep-work.pdf", PDF_BYTES, "application/pdf"))
    app.button[0].click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "deep-work.pdf is ready in SmartRead." in page_text
    assert "deep-work.pdf" in page_text
    assert "uploaded" in page_text


def test_streamlit_extracts_uploaded_pdf_and_shows_summary(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 7,
            "original_filename": "learning.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-27T12:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "not_started",
            "error_message": None,
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_extract_pdf_text_from_api(api_base_url: str, *, book_id: int) -> ExtractionResult:
        uploaded_books[0]["processing_status"] = "extracted"
        return ExtractionResult(
            success=True,
            message="Extraction complete: 2 pages, 2 with text, 0 blank.",
            summary={"page_count": 2, "text_page_count": 2, "blank_page_count": 0},
            book=uploaded_books[0],
            pages=[
                {
                    "book_id": book_id,
                    "page_number": 1,
                    "source_location": "book:7:page:1",
                    "extracted_text": "First page",
                }
            ],
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(uploads_module, "extract_pdf_text_from_api", fake_extract_pdf_text_from_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    app.button[1].click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "learning.pdf" in page_text
    assert "Extraction complete: 2 pages, 2 with text, 0 blank." in page_text
    assert "extracted" in page_text


def test_streamlit_shows_retryable_extraction_failure(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 8,
            "original_filename": "corrupt.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-27T12:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "not_started",
            "error_message": None,
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_extract_pdf_text_from_api(api_base_url: str, *, book_id: int) -> ExtractionResult:
        return ExtractionResult(
            success=False,
            message="Text extraction failed. Retry extraction or upload a cleaner PDF.",
            summary={},
            book={
                **uploaded_books[0],
                "processing_status": "extraction_failed",
                "error_message": "Text extraction failed. Retry extraction or upload a cleaner PDF.",
            },
            retryable=True,
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(uploads_module, "extract_pdf_text_from_api", fake_extract_pdf_text_from_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    app.button[1].click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Text extraction failed. Retry extraction or upload a cleaner PDF." in page_text
    assert "Retry extraction or upload a cleaner PDF." in page_text


def test_streamlit_detects_chapters_and_shows_book_map(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 9,
            "original_filename": "chapters.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-27T12:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "not_started",
            "chapter_detection_confidence": None,
            "chapter_detection_message": None,
        }
    ]

    chapters = [
        {
            "book_id": 9,
            "chapter_number": 1,
            "title": "Getting Started",
            "start_page": 1,
            "end_page": 3,
            "start_source_location": "book:9:page:1",
            "end_source_location": "book:9:page:3",
            "confidence": "high",
            "detection_source": "heading_pattern",
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_detect_chapters_from_api(api_base_url: str, *, book_id: int) -> ChapterDetectionResult:
        uploaded_books[0]["chapter_detection_status"] = "detected"
        uploaded_books[0]["chapter_detection_confidence"] = "high"
        return ChapterDetectionResult(
            success=True,
            message="Detected 1 chapters with high confidence.",
            summary={"chapter_count": 1, "confidence": "high", "warning": None},
            chapters=chapters,
            book=uploaded_books[0],
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(uploads_module, "detect_chapters_from_api", fake_detect_chapters_from_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    app.button[2].click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Detected 1 chapters with high confidence." in page_text
    assert "Detected Chapters" in page_text
    assert "1. Getting Started" in page_text
    assert "Pages 1-3" in page_text
    assert "Chapter lesson generation remains unavailable until boundaries are reviewed." in page_text


def test_streamlit_shows_low_confidence_chapter_detection_warning(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 10,
            "original_filename": "weak-headings.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-27T12:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "not_started",
            "chapter_detection_confidence": None,
            "chapter_detection_message": None,
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_detect_chapters_from_api(api_base_url: str, *, book_id: int) -> ChapterDetectionResult:
        return ChapterDetectionResult(
            success=True,
            message="Detected 1 chapters with low confidence.",
            summary={
                "chapter_count": 1,
                "confidence": "low",
                "warning": "Chapter detection confidence is low. Review boundaries before generating lessons.",
            },
            chapters=[
                {
                    "book_id": book_id,
                    "chapter_number": 1,
                    "title": "Foundations",
                    "start_page": 1,
                    "end_page": 2,
                    "start_source_location": "book:10:page:1",
                    "end_source_location": "book:10:page:2",
                    "confidence": "low",
                    "detection_source": "numbered_heading_pattern",
                }
            ],
            book=uploaded_books[0],
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(uploads_module, "detect_chapters_from_api", fake_detect_chapters_from_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    app.button[2].click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Detected 1 chapters with low confidence." in page_text
    assert "Chapter detection confidence is low. Review boundaries before generating lessons." in page_text
    assert "1. Foundations" in page_text


def test_streamlit_shows_empty_state_when_no_chapters_are_detected(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 11,
            "original_filename": "essay.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-27T12:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "not_started",
            "chapter_detection_confidence": None,
            "chapter_detection_message": None,
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_detect_chapters_from_api(api_base_url: str, *, book_id: int) -> ChapterDetectionResult:
        return ChapterDetectionResult(
            success=True,
            message="No chapters could be detected. Manual chapter review will be required.",
            summary={
                "chapter_count": 0,
                "confidence": "none",
                "warning": "No chapters could be detected. Manual chapter review will be required.",
            },
            chapters=[],
            book=uploaded_books[0],
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(uploads_module, "detect_chapters_from_api", fake_detect_chapters_from_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    app.button[2].click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "No chapters could be detected." in page_text
    assert "Manual chapter review will be required before lessons." in page_text
    assert "Chapter lesson generation remains unavailable until boundaries are reviewed." in page_text


def test_streamlit_saves_reviewed_chapter_boundaries(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 12,
            "original_filename": "review.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-27T12:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "not_started",
        }
    ]
    detected_chapters = [
        {
            "book_id": 12,
            "chapter_number": 1,
            "title": "Focus",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:12:page:1",
            "end_source_location": "book:12:page:2",
            "confidence": "high",
            "detection_source": "heading_pattern",
        }
    ]
    saved_payload: dict[str, object] = {}

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_detect_chapters_from_api(api_base_url: str, *, book_id: int) -> ChapterDetectionResult:
        return ChapterDetectionResult(
            success=True,
            message="Detected 1 chapters with high confidence.",
            summary={"chapter_count": 1, "confidence": "high", "warning": None},
            chapters=detected_chapters,
            book=uploaded_books[0],
        )

    def fake_save_chapter_boundaries_to_api(
        api_base_url: str,
        *,
        book_id: int,
        chapters: list[dict[str, object]],
    ) -> ChapterBoundaryReviewResult:
        saved_payload["book_id"] = book_id
        saved_payload["chapters"] = chapters
        uploaded_books[0]["chapter_review_status"] = "accepted"
        return ChapterBoundaryReviewResult(
            success=True,
            message="Accepted 1 reviewed chapter boundary.",
            chapters=[
                {
                    "book_id": book_id,
                    "chapter_number": 1,
                    "title": "Renamed Focus",
                    "start_page": 1,
                    "end_page": 1,
                    "start_source_location": "book:12:page:1",
                    "end_source_location": "book:12:page:1",
                    "review_status": "accepted",
                }
            ],
            book=uploaded_books[0],
        )

    def fake_get_chapter_summary_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ChapterSummaryResult:
        return ChapterSummaryResult(
            success=False,
            message="Chapter Summary has not been generated yet.",
            retryable=False,
        )

    def fake_get_concepts_takeaways_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ConceptsTakeawaysResult:
        return ConceptsTakeawaysResult(
            success=False,
            message="Core Concepts and Key Takeaways have not been generated yet.",
            retryable=False,
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(uploads_module, "detect_chapters_from_api", fake_detect_chapters_from_api)
    monkeypatch.setattr(
        uploads_module,
        "save_chapter_boundaries_to_api",
        fake_save_chapter_boundaries_to_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_summary_from_api",
        fake_get_chapter_summary_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_concepts_takeaways_from_api",
        fake_get_concepts_takeaways_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", _empty_quiz_result)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    app.button[2].click()
    app.run(timeout=5)
    app.text_input[0].set_value("Renamed Focus")
    app.number_input[1].set_value(1)
    app.button[5].click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert saved_payload["book_id"] == 12
    assert saved_payload["chapters"] == [
        {"chapter_number": 1, "title": "Renamed Focus", "start_page": 1, "end_page": 1}
    ]
    assert "Accepted 1 reviewed chapter boundary." in page_text
    assert "Accepted chapter boundaries are saved for downstream lesson generation." in page_text


def test_streamlit_generates_selected_chapter_summary(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 13,
            "original_filename": "summary.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 13,
            "chapter_number": 1,
            "title": "Deep Focus",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:13:page:1",
            "end_source_location": "book:13:page:2",
            "review_status": "accepted",
        }
    ]
    generated: dict[str, object] = {}

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_generate_chapter_summary_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ChapterSummaryResult:
        generated["book_id"] = book_id
        generated["chapter_number"] = chapter_number
        return ChapterSummaryResult(
            success=True,
            message="Summary generated for Chapter 1: Deep Focus.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            summary={
                "central_argument": {
                    "claim": "Focus improves when attention is protected.",
                    "citation_ids": ["c1"],
                },
                "supporting_ideas": [
                    {
                        "claim": "Protected attention makes deep work possible.",
                        "citation_ids": ["c1"],
                    }
                ],
                "citations": [
                    {
                        "id": "c1",
                        "source_location": "book:13:page:1",
                        "page_number": 1,
                        "source_excerpt": "Focus improves when attention is protected.",
                    }
                ],
            },
        )

    def fake_get_chapter_summary_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ChapterSummaryResult:
        return ChapterSummaryResult(
            success=False,
            message="Chapter Summary has not been generated yet.",
            retryable=False,
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "generate_chapter_summary_from_api",
        fake_generate_chapter_summary_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_summary_from_api",
        fake_get_chapter_summary_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", _empty_quiz_result)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    generate_button = next(
        button for button in app.button if button.label == "Generate summary: 1. Deep Focus"
    )
    generate_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert generated == {"book_id": 13, "chapter_number": 1}
    assert "Summary generated for Chapter 1: Deep Focus." in page_text
    assert "Focus improves when attention is protected." in page_text
    assert "Protected attention makes deep work possible." in page_text


def test_streamlit_shows_retryable_summary_generation_failure(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 14,
            "original_filename": "unsupported-summary.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 14,
            "chapter_number": 1,
            "title": "Evidence",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:14:page:1",
            "end_source_location": "book:14:page:2",
            "review_status": "accepted",
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_generate_chapter_summary_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ChapterSummaryResult:
        return ChapterSummaryResult(
            success=False,
            message="Source excerpts must support cited claims.",
            chapter=accepted_chapters[0],
            generation_status="failed",
            retryable=True,
        )

    def fake_get_chapter_summary_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ChapterSummaryResult:
        return ChapterSummaryResult(
            success=False,
            message="Chapter Summary has not been generated yet.",
            retryable=False,
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "generate_chapter_summary_from_api",
        fake_generate_chapter_summary_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_summary_from_api",
        fake_get_chapter_summary_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", _empty_quiz_result)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    generate_button = next(
        button for button in app.button if button.label == "Generate summary: 1. Evidence"
    )
    generate_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Source excerpts must support cited claims." in page_text
    assert "Retry summary generation for this chapter." in page_text


def test_streamlit_loads_persisted_chapter_summary(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 15,
            "original_filename": "persisted-summary.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 15,
            "chapter_number": 1,
            "title": "Persisted Focus",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:15:page:1",
            "end_source_location": "book:15:page:2",
            "review_status": "accepted",
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_chapter_summary_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ChapterSummaryResult:
        return ChapterSummaryResult(
            success=True,
            message="Summary loaded for Chapter 1: Persisted Focus.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            summary={
                "central_argument": {
                    "claim": "Persisted summaries should be visible after restart.",
                    "citation_ids": ["c1"],
                },
                "supporting_ideas": [],
                "citations": [],
            },
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_summary_from_api",
        fake_get_chapter_summary_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", _empty_quiz_result)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Summary loaded for Chapter 1: Persisted Focus." in page_text
    assert "Persisted summaries should be visible after restart." in page_text


def test_streamlit_clicking_summary_citation_updates_evidence_panel(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 16,
            "original_filename": "clickable-citations.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 16,
            "chapter_number": 1,
            "title": "Evidence Focus",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:16:page:1",
            "end_source_location": "book:16:page:2",
            "review_status": "accepted",
        }
    ]
    loaded_evidence: dict[str, object] = {}

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_chapter_summary_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ChapterSummaryResult:
        return ChapterSummaryResult(
            success=True,
            message="Summary loaded for Chapter 1: Evidence Focus.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            summary={
                "central_argument": {
                    "claim": "Focus improves when attention is protected.",
                    "citation_ids": ["c1"],
                },
                "supporting_ideas": [],
                "citations": [
                    {
                        "id": "c1",
                        "source_location": "book:16:page:1",
                        "page_number": 1,
                        "source_excerpt": "Focus improves when attention is protected.",
                    }
                ],
            },
        )

    def fake_get_citation_evidence_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
        citation_id: str,
    ) -> CitationEvidenceResult:
        loaded_evidence["book_id"] = book_id
        loaded_evidence["chapter_number"] = chapter_number
        loaded_evidence["citation_id"] = citation_id
        return CitationEvidenceResult(
            success=True,
            message="Citation c1 is verified.",
            citation_id="c1",
            verification_status="verified",
            source_location="book:16:page:1",
            page_number=1,
            source_excerpt="Focus improves when attention is protected.",
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_summary_from_api",
        fake_get_chapter_summary_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_citation_evidence_from_api",
        fake_get_citation_evidence_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", _empty_quiz_result)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    citation_button = next(button for button in app.button if button.label == "Citation c1")
    citation_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert loaded_evidence == {"book_id": 16, "chapter_number": 1, "citation_id": "c1"}
    assert "Focus improves when attention is protected." in page_text
    assert "Verified evidence" in page_text
    assert "Page 1" in page_text
    assert "book:16:page:1" in page_text


def test_streamlit_evidence_error_can_retry_same_citation(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 17,
            "original_filename": "retry-evidence.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 17,
            "chapter_number": 1,
            "title": "Retry Evidence",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:17:page:1",
            "end_source_location": "book:17:page:2",
            "review_status": "accepted",
        }
    ]
    evidence_results = [
        CitationEvidenceResult(
            success=False,
            message="Evidence could not be loaded. Check the FastAPI backend, then try again.",
            citation_id="c1",
            retryable=True,
        ),
        CitationEvidenceResult(
            success=True,
            message="Citation c1 is verified.",
            citation_id="c1",
            verification_status="verified",
            source_location="book:17:page:1",
            page_number=1,
            source_excerpt="Retry loads the same focused excerpt.",
        ),
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_chapter_summary_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ChapterSummaryResult:
        return ChapterSummaryResult(
            success=True,
            message="Summary loaded for Chapter 1: Retry Evidence.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            summary={
                "central_argument": {
                    "claim": "Retry keeps the learner in the current chapter.",
                    "citation_ids": ["c1"],
                },
                "supporting_ideas": [],
                "citations": [
                    {
                        "id": "c1",
                        "source_location": "book:17:page:1",
                        "page_number": 1,
                        "source_excerpt": "Retry loads the same focused excerpt.",
                    }
                ],
            },
        )

    def fake_get_citation_evidence_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
        citation_id: str,
    ) -> CitationEvidenceResult:
        return evidence_results.pop(0)

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_summary_from_api",
        fake_get_chapter_summary_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_citation_evidence_from_api",
        fake_get_citation_evidence_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", _empty_quiz_result)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    citation_button = next(button for button in app.button if button.label == "Citation c1")
    citation_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)
    assert "Evidence could not be loaded. Check the FastAPI backend, then try again." in page_text
    assert "Retry keeps the learner in the current chapter." in page_text

    retry_button = next(button for button in app.button if button.label == "Retry evidence c1")
    retry_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)
    assert "Retry loads the same focused excerpt." in page_text
    assert "Verified evidence" in page_text


def test_streamlit_generates_core_concepts_and_key_takeaways(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 18,
            "original_filename": "concept-tabs.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 18,
            "chapter_number": 1,
            "title": "Learning Hooks",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:18:page:1",
            "end_source_location": "book:18:page:2",
            "review_status": "accepted",
        }
    ]
    generated: dict[str, object] = {}

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_concepts_takeaways_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ConceptsTakeawaysResult:
        return ConceptsTakeawaysResult(
            success=False,
            message="Core Concepts and Key Takeaways have not been generated yet.",
            retryable=False,
        )

    def fake_generate_concepts_takeaways_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ConceptsTakeawaysResult:
        generated["book_id"] = book_id
        generated["chapter_number"] = chapter_number
        return ConceptsTakeawaysResult(
            success=True,
            message="Core Concepts and Key Takeaways generated for Chapter 1: Learning Hooks.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            content={
                "core_concepts": [
                    {
                        "name": "Protected Attention",
                        "explanation": "Protected attention reduces switching.",
                        "why_it_matters": "It keeps deliberate practice on track.",
                        "example": "A learner silences chat before reading.",
                        "citation_ids": ["c1"],
                    }
                ],
                "key_takeaways": [
                    {
                        "text": "Protect attention before difficult practice.",
                        "citation_ids": ["c1"],
                    }
                ],
                "citations": [
                    {
                        "id": "c1",
                        "source_location": "book:18:page:1",
                        "page_number": 1,
                        "source_excerpt": "Protected attention reduces switching.",
                    }
                ],
            },
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_concepts_takeaways_from_api",
        fake_get_concepts_takeaways_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "generate_concepts_takeaways_from_api",
        fake_generate_concepts_takeaways_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_chapter_summary_from_api", _empty_summary_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", _empty_quiz_result)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    generate_button = next(
        button
        for button in app.button
        if button.label == "Generate concepts and takeaways: 1. Learning Hooks"
    )
    generate_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert generated == {"book_id": 18, "chapter_number": 1}
    assert "Core Concepts and Key Takeaways generated for Chapter 1: Learning Hooks." in page_text
    assert "Protected Attention" in page_text
    assert "Protected attention reduces switching." in page_text
    assert "It keeps deliberate practice on track." in page_text
    assert "Protect attention before difficult practice." in page_text


def test_streamlit_shows_retryable_concepts_takeaways_failure(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 19,
            "original_filename": "unsupported-concepts.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 19,
            "chapter_number": 1,
            "title": "Unsupported Claims",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:19:page:1",
            "end_source_location": "book:19:page:2",
            "review_status": "accepted",
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_chapter_summary_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ChapterSummaryResult:
        return ChapterSummaryResult(
            success=False,
            message="Chapter Summary has not been generated yet.",
            retryable=False,
        )

    def fake_get_concepts_takeaways_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ConceptsTakeawaysResult:
        return ConceptsTakeawaysResult(
            success=False,
            message="Core Concepts and Key Takeaways have not been generated yet.",
            retryable=False,
        )

    def fake_generate_concepts_takeaways_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ConceptsTakeawaysResult:
        return ConceptsTakeawaysResult(
            success=False,
            message="Source excerpts must support concept and takeaway claims.",
            chapter=accepted_chapters[0],
            generation_status="failed",
            retryable=True,
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_summary_from_api",
        fake_get_chapter_summary_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_concepts_takeaways_from_api",
        fake_get_concepts_takeaways_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "generate_concepts_takeaways_from_api",
        fake_generate_concepts_takeaways_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", _empty_quiz_result)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    generate_button = next(
        button
        for button in app.button
        if button.label == "Generate concepts and takeaways: 1. Unsupported Claims"
    )
    generate_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Source excerpts must support concept and takeaway claims." in page_text
    assert "Retry Core Concepts and Key Takeaways generation for this chapter." in page_text


def test_streamlit_generates_five_quiz_questions_without_grading(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 20,
            "original_filename": "quiz-tabs.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 20,
            "chapter_number": 1,
            "title": "Quiz Practice",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:20:page:1",
            "end_source_location": "book:20:page:2",
            "review_status": "accepted",
        }
    ]
    generated: dict[str, object] = {}

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_chapter_summary_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ChapterSummaryResult:
        return ChapterSummaryResult(
            success=False,
            message="Chapter Summary has not been generated yet.",
            retryable=False,
        )

    def fake_get_concepts_takeaways_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> ConceptsTakeawaysResult:
        return ConceptsTakeawaysResult(
            success=False,
            message="Core Concepts and Key Takeaways have not been generated yet.",
            retryable=False,
        )

    def fake_get_quiz_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> QuizResult:
        return QuizResult(
            success=False,
            message="Quiz has not been generated yet.",
            retryable=False,
        )

    def fake_generate_quiz_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> QuizResult:
        generated["book_id"] = book_id
        generated["chapter_number"] = chapter_number
        return QuizResult(
            success=True,
            message="Quiz generated for Chapter 1: Quiz Practice.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            quiz={
                "questions": [
                    {
                        "id": "q1",
                        "question_text": (
                            "What does protected attention reduce during deliberate practice?"
                        ),
                        "question_type": "multiple_choice",
                        "answer_options": [
                            "Constant switching",
                            "Long-term memory",
                            "Chapter boundaries",
                        ],
                        "correct_answer": "Constant switching",
                        "explanation": "Protected attention reduces constant switching.",
                        "tested_concept": "Protected Attention",
                        "citation_id": "qc1",
                    },
                    {
                        "id": "q2",
                        "question_text": "True or false: retrieval cues help recall.",
                        "question_type": "true_false",
                        "answer_options": ["True", "False"],
                        "correct_answer": "True",
                        "explanation": "Retrieval cues help learners recall ideas.",
                        "tested_concept": "Retrieval Cues",
                        "citation_id": "qc2",
                    },
                    {
                        "id": "q3",
                        "question_text": "Which concept applies when a learner silences chat?",
                        "question_type": "scenario_application",
                        "answer_options": ["Protected Attention", "Retrieval Cues"],
                        "correct_answer": "Protected Attention",
                        "explanation": "Silencing chat protects attention.",
                        "tested_concept": "Protected Attention",
                        "citation_id": "qc1",
                    },
                    {
                        "id": "q4",
                        "question_text": "Which practice connects ideas to memory?",
                        "question_type": "multiple_choice",
                        "answer_options": ["Retrieval cues", "Ignoring feedback"],
                        "correct_answer": "Retrieval cues",
                        "explanation": "Retrieval cues connect practice to memory.",
                        "tested_concept": "Retrieval Cues",
                        "citation_id": "qc2",
                    },
                    {
                        "id": "q5",
                        "question_text": "What makes deliberate practice easier to repeat?",
                        "question_type": "multiple_choice",
                        "answer_options": ["Reducing context switching", "Removing citations"],
                        "correct_answer": "Reducing context switching",
                        "explanation": "Protected blocks reduce context switching.",
                        "tested_concept": "Protected Attention",
                        "citation_id": "qc1",
                    },
                ],
                "citations": [
                    {
                        "id": "qc1",
                        "source_location": "book:20:page:1",
                        "page_number": 1,
                        "source_excerpt": "Protected attention reduces constant switching.",
                    }
                ],
            },
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_summary_from_api",
        fake_get_chapter_summary_from_api,
    )
    monkeypatch.setattr(
        uploads_module,
        "get_concepts_takeaways_from_api",
        fake_get_concepts_takeaways_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", fake_get_quiz_from_api)
    monkeypatch.setattr(uploads_module, "get_quiz_progress_from_api", _empty_quiz_progress_result)
    monkeypatch.setattr(uploads_module, "generate_quiz_from_api", fake_generate_quiz_from_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    generate_button = next(
        button for button in app.button if button.label == "Generate quiz: 1. Quiz Practice"
    )
    generate_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert generated == {"book_id": 20, "chapter_number": 1}
    assert "Quiz generated for Chapter 1: Quiz Practice." in page_text
    assert "What does protected attention reduce during deliberate practice?" in page_text
    assert "Constant switching" in page_text
    assert "Protected Attention" in page_text
    assert "Correct answer:" not in page_text


def test_streamlit_loads_persisted_quiz_questions(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 21,
            "original_filename": "persisted-quiz.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 21,
            "chapter_number": 1,
            "title": "Persisted Quiz",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:21:page:1",
            "end_source_location": "book:21:page:2",
            "review_status": "accepted",
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_quiz_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> QuizResult:
        return QuizResult(
            success=True,
            message="Quiz loaded for Chapter 1: Persisted Quiz.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            quiz=_sample_quiz_content(),
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_chapter_summary_from_api", _empty_summary_result)
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", fake_get_quiz_from_api)
    monkeypatch.setattr(uploads_module, "get_quiz_progress_from_api", _empty_quiz_progress_result)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Quiz loaded for Chapter 1: Persisted Quiz." in page_text
    assert "What does protected attention reduce?" in page_text
    assert "Tested concept: Protected Attention" in page_text


def test_streamlit_reloads_persisted_quiz_progress(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 24,
            "original_filename": "saved-progress.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 24,
            "chapter_number": 1,
            "title": "Saved Progress",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:24:page:1",
            "end_source_location": "book:24:page:2",
            "review_status": "accepted",
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_quiz_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> QuizResult:
        return QuizResult(
            success=True,
            message="Quiz loaded for Chapter 1: Saved Progress.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            quiz=_sample_quiz_content(),
        )

    def fake_get_quiz_progress_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> QuizProgressResult:
        return QuizProgressResult(
            success=True,
            message="Quiz progress loaded.",
            progress={
                "answered_count": 1,
                "correct_count": 1,
                "incorrect_count": 0,
                "total_questions": 5,
            },
            answers=[
                {
                    "question_id": "q1",
                    "selected_answer": "Constant switching",
                    "is_correct": True,
                    "correct_answer": "Constant switching",
                    "explanation": "Protected attention reduces constant switching.",
                    "tested_concept": "Protected Attention",
                    "citation_id": "qc1",
                    "source_location": "book:24:page:1",
                    "page_number": 1,
                    "source_excerpt": "Protected attention reduces constant switching.",
                    "progress": {
                        "answered_count": 1,
                        "correct_count": 1,
                        "incorrect_count": 0,
                        "total_questions": 5,
                    },
                }
            ],
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_chapter_summary_from_api", _empty_summary_result)
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", fake_get_quiz_from_api)
    monkeypatch.setattr(uploads_module, "get_quiz_progress_from_api", fake_get_quiz_progress_from_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Quiz loaded for Chapter 1: Saved Progress." in page_text
    assert "Correct." in page_text
    assert "Source excerpt: Protected attention reduces constant switching." in page_text
    assert "Answered: 1 of 5" in page_text
    assert "Correct: 1" in page_text
    assert "Incorrect: 0" in page_text


def test_streamlit_submits_quiz_answer_and_updates_mastery(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 23,
            "original_filename": "feedback-quiz.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 23,
            "chapter_number": 1,
            "title": "Feedback Quiz",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:23:page:1",
            "end_source_location": "book:23:page:2",
            "review_status": "accepted",
        }
    ]
    submitted: dict[str, object] = {}

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_quiz_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> QuizResult:
        return QuizResult(
            success=True,
            message="Quiz loaded for Chapter 1: Feedback Quiz.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            quiz=_sample_quiz_content(),
        )

    def fake_submit_quiz_answer_to_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
        question_id: str,
        selected_answer: str,
    ) -> QuizAnswerResult:
        submitted.update(
            {
                "book_id": book_id,
                "chapter_number": chapter_number,
                "question_id": question_id,
                "selected_answer": selected_answer,
            }
        )
        return QuizAnswerResult(
            success=True,
            message="Incorrect.",
            question_id=question_id,
            selected_answer=selected_answer,
            is_correct=False,
            correct_answer="Constant switching",
            explanation="Protected attention reduces constant switching.",
            tested_concept="Protected Attention",
            citation_id="qc1",
            source_location="book:23:page:1",
            page_number=1,
            source_excerpt="Protected attention reduces constant switching.",
            progress={
                "answered_count": 1,
                "correct_count": 0,
                "incorrect_count": 1,
                "total_questions": 5,
            },
        )

    def fake_get_missed_concepts_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> MissedConceptsResult:
        if not submitted:
            return _empty_missed_concepts_result(
                api_base_url,
                book_id=book_id,
                chapter_number=chapter_number,
            )
        return MissedConceptsResult(
            success=True,
            message="Missed Concepts loaded.",
            summary={"missed_concept_count": 1},
            missed_concepts=[
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "concept_name": "Protected Attention",
                    "question_id": "q1",
                    "quiz_answer_id": 1,
                    "explanation": "Protected attention reduces constant switching.",
                    "citation_id": "qc1",
                    "source_location": "book:23:page:1",
                    "page_number": 1,
                    "source_excerpt": "Protected attention reduces constant switching.",
                }
            ],
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_chapter_summary_from_api", _empty_summary_result)
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", fake_get_quiz_from_api)
    monkeypatch.setattr(uploads_module, "get_quiz_progress_from_api", _empty_quiz_progress_result)
    monkeypatch.setattr(uploads_module, "submit_quiz_answer_to_api", fake_submit_quiz_answer_to_api)
    monkeypatch.setattr(
        uploads_module,
        "get_missed_concepts_from_api",
        fake_get_missed_concepts_from_api,
    )

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    answer_radio = next(radio for radio in app.radio if radio.label == "Answer for q1")
    answer_radio.set_value("Long-term memory")
    submit_button = next(button for button in app.button if button.label == "Submit answer q1")
    submit_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert submitted == {
        "book_id": 23,
        "chapter_number": 1,
        "question_id": "q1",
        "selected_answer": "Long-term memory",
    }
    assert "Incorrect." in page_text
    assert "Correct answer: Constant switching" in page_text
    assert "Protected attention reduces constant switching." in page_text
    assert "Tested concept: Protected Attention" in page_text
    assert "Source excerpt: Protected attention reduces constant switching." in page_text
    assert "Answered: 1 of 5" in page_text
    assert "Correct: 0" in page_text
    assert "Incorrect: 1" in page_text
    assert "Missed Concepts" in page_text
    assert "Question: q1" in page_text


def test_streamlit_shows_recoverable_quiz_answer_feedback_failure(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 25,
            "original_filename": "feedback-failure.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 25,
            "chapter_number": 1,
            "title": "Feedback Failure",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:25:page:1",
            "end_source_location": "book:25:page:2",
            "review_status": "accepted",
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_quiz_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> QuizResult:
        return QuizResult(
            success=True,
            message="Quiz loaded for Chapter 1: Feedback Failure.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            quiz=_sample_quiz_content(),
        )

    def fake_submit_quiz_answer_to_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
        question_id: str,
        selected_answer: str,
    ) -> QuizAnswerResult:
        return QuizAnswerResult(
            success=False,
            message="Answer feedback failed. Check the FastAPI backend, then try again.",
            question_id=question_id,
            retryable=True,
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_chapter_summary_from_api", _empty_summary_result)
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", fake_get_quiz_from_api)
    monkeypatch.setattr(uploads_module, "get_quiz_progress_from_api", _empty_quiz_progress_result)
    monkeypatch.setattr(uploads_module, "submit_quiz_answer_to_api", fake_submit_quiz_answer_to_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    answer_radio = next(radio for radio in app.radio if radio.label == "Answer for q1")
    answer_radio.set_value("Long-term memory")
    submit_button = next(button for button in app.button if button.label == "Submit answer q1")
    submit_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Answer feedback failed. Check the FastAPI backend, then try again." in page_text
    assert "Retry checking this answer after FastAPI recovers." in page_text


def test_streamlit_review_tab_loads_missed_concepts(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 26,
            "original_filename": "missed-review.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 26,
            "chapter_number": 1,
            "title": "Missed Review",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:26:page:1",
            "end_source_location": "book:26:page:2",
            "review_status": "accepted",
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_missed_concepts_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> MissedConceptsResult:
        return MissedConceptsResult(
            success=True,
            message="Missed Concepts loaded.",
            summary={"missed_concept_count": 1},
            missed_concepts=[
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "concept_name": "Protected Attention",
                    "question_id": "q1",
                    "quiz_answer_id": 3,
                    "explanation": "Protected attention reduces constant switching.",
                    "citation_id": "qc1",
                    "source_location": "book:26:page:1",
                    "page_number": 1,
                    "source_excerpt": "Protected attention reduces constant switching.",
                }
            ],
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_chapter_summary_from_api", _empty_summary_result)
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", _empty_quiz_result)
    monkeypatch.setattr(
        uploads_module,
        "get_missed_concepts_from_api",
        fake_get_missed_concepts_from_api,
    )

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Missed Concepts" in page_text
    assert "Protected Attention" in page_text
    assert "Question: q1" in page_text
    assert "Protected attention reduces constant switching." in page_text
    assert "Citation qc1" in page_text
    assert "Source excerpt: Protected attention reduces constant switching." in page_text


def test_streamlit_review_tab_retries_only_missed_questions(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 28,
            "original_filename": "retry-missed.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 28,
            "chapter_number": 1,
            "title": "Retry Misses",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:28:page:1",
            "end_source_location": "book:28:page:2",
            "review_status": "accepted",
        }
    ]
    retried: dict[str, object] = {}

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_quiz_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> QuizResult:
        return QuizResult(
            success=True,
            message="Quiz loaded for Chapter 1: Retry Misses.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            quiz=_sample_quiz_content(),
        )

    def fake_get_quiz_progress_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> QuizProgressResult:
        return QuizProgressResult(
            success=True,
            message="Quiz progress loaded.",
            progress={
                "answered_count": 1,
                "correct_count": 0,
                "incorrect_count": 1,
                "total_questions": 5,
            },
            answers=[
                {
                    "question_id": "q1",
                    "selected_answer": "Long-term memory",
                    "is_correct": False,
                    "correct_answer": "Constant switching",
                    "explanation": "Protected attention reduces constant switching.",
                    "tested_concept": "Protected Attention",
                    "citation_id": "qc1",
                    "source_location": "book:28:page:1",
                    "page_number": 1,
                    "source_excerpt": "Protected attention reduces constant switching.",
                    "progress": {
                        "answered_count": 1,
                        "correct_count": 0,
                        "incorrect_count": 1,
                        "total_questions": 5,
                    },
                }
            ],
        )

    def fake_get_missed_concepts_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> MissedConceptsResult:
        if retried:
            return _empty_missed_concepts_result(
                api_base_url,
                book_id=book_id,
                chapter_number=chapter_number,
            )
        return MissedConceptsResult(
            success=True,
            message="Missed Concepts loaded.",
            summary={"missed_concept_count": 1},
            missed_concepts=[
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "concept_name": "Protected Attention",
                    "question_id": "q1",
                    "quiz_answer_id": 3,
                    "explanation": "Protected attention reduces constant switching.",
                    "citation_id": "qc1",
                    "source_location": "book:28:page:1",
                    "page_number": 1,
                    "source_excerpt": "Protected attention reduces constant switching.",
                }
            ],
        )

    def fake_retry_missed_question_to_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
        question_id: str,
        selected_answer: str,
    ) -> QuizAnswerResult:
        retried.update(
            {
                "book_id": book_id,
                "chapter_number": chapter_number,
                "question_id": question_id,
                "selected_answer": selected_answer,
            }
        )
        return QuizAnswerResult(
            success=True,
            message="Correct.",
            question_id=question_id,
            selected_answer=selected_answer,
            is_correct=True,
            correct_answer="Constant switching",
            explanation="Protected attention reduces constant switching.",
            tested_concept="Protected Attention",
            citation_id="qc1",
            source_location="book:28:page:1",
            page_number=1,
            source_excerpt="Protected attention reduces constant switching.",
            progress={
                "answered_count": 1,
                "correct_count": 1,
                "incorrect_count": 0,
                "total_questions": 5,
            },
            missed_concept_status="resolved",
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_chapter_summary_from_api", _empty_summary_result)
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", fake_get_quiz_from_api)
    monkeypatch.setattr(uploads_module, "get_quiz_progress_from_api", fake_get_quiz_progress_from_api)
    monkeypatch.setattr(uploads_module, "get_missed_concepts_from_api", fake_get_missed_concepts_from_api)
    monkeypatch.setattr(uploads_module, "retry_missed_question_to_api", fake_retry_missed_question_to_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)
    assert "Retry answer for q1" in [radio.label for radio in app.radio]
    assert "Retry answer for q2" not in [radio.label for radio in app.radio]
    assert "Question: q1" in page_text

    retry_radio = next(radio for radio in app.radio if radio.label == "Retry answer for q1")
    retry_radio.set_value("Constant switching")
    retry_button = next(button for button in app.button if button.label == "Retry missed question q1")
    retry_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert retried == {
        "book_id": 28,
        "chapter_number": 1,
        "question_id": "q1",
        "selected_answer": "Constant switching",
    }
    assert "Missed Concept resolved." in page_text
    assert "Answered: 1 of 5" in page_text
    assert "Correct: 1" in page_text
    assert "Incorrect: 0" in page_text
    assert "No missed concepts are due from checked answers." in page_text


def test_streamlit_review_tab_shows_recoverable_retry_failure(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 29,
            "original_filename": "retry-failure.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 29,
            "chapter_number": 1,
            "title": "Retry Failure",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:29:page:1",
            "end_source_location": "book:29:page:2",
            "review_status": "accepted",
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_quiz_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> QuizResult:
        return QuizResult(
            success=True,
            message="Quiz loaded for Chapter 1: Retry Failure.",
            chapter=accepted_chapters[0],
            generation_status="generated",
            quiz=_sample_quiz_content(),
        )

    def fake_get_missed_concepts_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> MissedConceptsResult:
        return MissedConceptsResult(
            success=True,
            message="Missed Concepts loaded.",
            summary={"missed_concept_count": 1},
            missed_concepts=[
                {
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "concept_name": "Protected Attention",
                    "question_id": "q1",
                    "quiz_answer_id": 3,
                    "explanation": "Protected attention reduces constant switching.",
                    "citation_id": "qc1",
                    "source_location": "book:29:page:1",
                    "page_number": 1,
                    "source_excerpt": "Protected attention reduces constant switching.",
                }
            ],
        )

    def fake_retry_missed_question_to_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
        question_id: str,
        selected_answer: str,
    ) -> QuizAnswerResult:
        return QuizAnswerResult(
            success=False,
            message="Retry failed. Check the FastAPI backend, then try again.",
            question_id=question_id,
            retryable=True,
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_chapter_summary_from_api", _empty_summary_result)
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", fake_get_quiz_from_api)
    monkeypatch.setattr(uploads_module, "get_quiz_progress_from_api", _empty_quiz_progress_result)
    monkeypatch.setattr(uploads_module, "get_missed_concepts_from_api", fake_get_missed_concepts_from_api)
    monkeypatch.setattr(uploads_module, "retry_missed_question_to_api", fake_retry_missed_question_to_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    retry_radio = next(radio for radio in app.radio if radio.label == "Retry answer for q1")
    retry_radio.set_value("Constant switching")
    retry_button = next(button for button in app.button if button.label == "Retry missed question q1")
    retry_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Retry failed. Check the FastAPI backend, then try again." in page_text
    assert "Retry this missed question after FastAPI recovers." in page_text
    assert "Question: q1" in page_text


def test_streamlit_review_tab_shows_recoverable_missed_concepts_error(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 27,
            "original_filename": "missed-error.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 27,
            "chapter_number": 1,
            "title": "Missed Error",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:27:page:1",
            "end_source_location": "book:27:page:2",
            "review_status": "accepted",
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_get_missed_concepts_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> MissedConceptsResult:
        return MissedConceptsResult(
            success=False,
            message="Missed Concepts could not be loaded. Check FastAPI, then try again.",
            summary={},
            missed_concepts=[],
            retryable=True,
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_chapter_summary_from_api", _empty_summary_result)
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", _empty_quiz_result)
    monkeypatch.setattr(
        uploads_module,
        "get_missed_concepts_from_api",
        fake_get_missed_concepts_from_api,
    )

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Missed Concepts could not be loaded. Check FastAPI, then try again." in page_text
    assert "Retry loading Missed Concepts after FastAPI recovers." in page_text


def test_streamlit_shows_retryable_quiz_generation_failure(monkeypatch):
    import smartread_frontend.health as health_module
    import smartread_frontend.uploads as uploads_module

    uploaded_books: list[dict[str, object]] = [
        {
            "id": 22,
            "original_filename": "failed-quiz.pdf",
            "content_type": "application/pdf",
            "file_size": len(PDF_BYTES),
            "uploaded_at": "2026-06-28T07:00:00Z",
            "upload_status": "uploaded",
            "processing_status": "extracted",
            "error_message": None,
            "chapter_detection_status": "detected",
            "chapter_detection_confidence": "high",
            "chapter_detection_message": None,
            "chapter_review_status": "accepted",
        }
    ]
    accepted_chapters = [
        {
            "book_id": 22,
            "chapter_number": 1,
            "title": "Failed Quiz",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:22:page:1",
            "end_source_location": "book:22:page:2",
            "review_status": "accepted",
        }
    ]

    def fake_get_api_status(api_base_url: str) -> ApiStatus:
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail="SmartRead API is available",
        )

    def fake_get_uploaded_books(api_base_url: str) -> BookListResult:
        return BookListResult(success=True, books=uploaded_books)

    def fake_get_chapter_boundaries_from_api(
        api_base_url: str,
        *,
        book_id: int,
    ) -> ChapterBoundaryListResult:
        return ChapterBoundaryListResult(success=True, chapters=accepted_chapters)

    def fake_generate_quiz_from_api(
        api_base_url: str,
        *,
        book_id: int,
        chapter_number: int,
    ) -> QuizResult:
        return QuizResult(
            success=False,
            message="Quiz questions need one clear correct answer.",
            chapter=accepted_chapters[0],
            generation_status="failed",
            retryable=True,
        )

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(
        uploads_module,
        "get_chapter_boundaries_from_api",
        fake_get_chapter_boundaries_from_api,
    )
    monkeypatch.setattr(uploads_module, "get_chapter_summary_from_api", _empty_summary_result)
    monkeypatch.setattr(uploads_module, "get_concepts_takeaways_from_api", _empty_concepts_result)
    monkeypatch.setattr(uploads_module, "get_quiz_from_api", _empty_quiz_result)
    monkeypatch.setattr(uploads_module, "generate_quiz_from_api", fake_generate_quiz_from_api)

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    generate_button = next(
        button for button in app.button if button.label == "Generate quiz: 1. Failed Quiz"
    )
    generate_button.click()
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert "Quiz questions need one clear correct answer." in page_text
    assert "Retry quiz generation for this chapter." in page_text
