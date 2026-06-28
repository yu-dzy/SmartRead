from pathlib import Path

from streamlit.testing.v1 import AppTest

from smartread_frontend.health import ApiStatus
from smartread_frontend.uploads import (
    BookListResult,
    ChapterBoundaryReviewResult,
    ChapterDetectionResult,
    ExtractionResult,
    UploadResult,
)


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


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

    monkeypatch.setattr(health_module, "get_api_status", fake_get_api_status)
    monkeypatch.setattr(uploads_module, "get_uploaded_books", fake_get_uploaded_books)
    monkeypatch.setattr(uploads_module, "detect_chapters_from_api", fake_detect_chapters_from_api)
    monkeypatch.setattr(
        uploads_module,
        "save_chapter_boundaries_to_api",
        fake_save_chapter_boundaries_to_api,
    )

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
