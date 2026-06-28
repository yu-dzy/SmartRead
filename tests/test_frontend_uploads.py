import httpx

from smartread_frontend.uploads import (
    detect_chapters_from_api,
    extract_pdf_text_from_api,
    get_uploaded_books,
    upload_pdf_to_api,
)


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def test_upload_pdf_to_api_sends_pdf_and_reports_success():
    captured_request: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["url"] = str(request.url)
        captured_request["content_type"] = request.headers["content-type"]
        return httpx.Response(
            201,
            json={
                "id": 1,
                "original_filename": "deep-work.pdf",
                "content_type": "application/pdf",
                "file_size": len(PDF_BYTES),
                "uploaded_at": "2026-06-27T12:00:00Z",
                "upload_status": "uploaded",
                "processing_status": "not_started",
                "error_message": None,
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = upload_pdf_to_api(
        "http://api.test",
        filename="deep-work.pdf",
        content=PDF_BYTES,
        content_type="application/pdf",
        client=client,
    )

    assert captured_request["method"] == "POST"
    assert captured_request["url"] == "http://api.test/books/uploads"
    assert captured_request["content_type"].startswith("multipart/form-data")
    assert result.success is True
    assert result.book is not None
    assert result.book["original_filename"] == "deep-work.pdf"
    assert result.message == "deep-work.pdf is ready in SmartRead."


def test_get_uploaded_books_returns_books_from_api():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "books": [
                    {
                        "id": 1,
                        "original_filename": "deep-work.pdf",
                        "content_type": "application/pdf",
                        "file_size": len(PDF_BYTES),
                        "uploaded_at": "2026-06-27T12:00:00Z",
                        "upload_status": "uploaded",
                        "processing_status": "not_started",
                        "error_message": None,
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_uploaded_books("http://api.test", client=client)

    assert result.success is True
    assert result.books[0]["original_filename"] == "deep-work.pdf"


def test_upload_pdf_to_api_reports_retryable_backend_error():
    failed_book = {
        "id": 1,
        "original_filename": "empty.pdf",
        "content_type": "application/pdf",
        "file_size": 0,
        "uploaded_at": "2026-06-27T12:00:00Z",
        "upload_status": "failed",
        "processing_status": "not_started",
        "error_message": "The PDF could not be read. Upload a valid PDF and try again.",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "detail": {
                    "message": failed_book["error_message"],
                    "retryable": True,
                    "book": failed_book,
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = upload_pdf_to_api(
        "http://api.test",
        filename="empty.pdf",
        content=b"",
        content_type="application/pdf",
        client=client,
    )

    assert result.success is False
    assert result.message == "The PDF could not be read. Upload a valid PDF and try again."
    assert result.retryable is True
    assert result.book == failed_book


def test_extract_pdf_text_from_api_reports_extraction_summary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://api.test/books/7/extraction"
        return httpx.Response(
            200,
            json={
                "book": {
                    "id": 7,
                    "original_filename": "learning.pdf",
                    "content_type": "application/pdf",
                    "file_size": 100,
                    "uploaded_at": "2026-06-27T12:00:00Z",
                    "upload_status": "uploaded",
                    "processing_status": "extracted",
                    "error_message": None,
                },
                "summary": {
                    "page_count": 2,
                    "text_page_count": 2,
                    "blank_page_count": 0,
                },
                "pages": [
                    {
                        "book_id": 7,
                        "page_number": 1,
                        "source_location": "book:7:page:1",
                        "extracted_text": "First page",
                    }
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = extract_pdf_text_from_api("http://api.test", book_id=7, client=client)

    assert result.success is True
    assert result.message == "Extraction complete: 2 pages, 2 with text, 0 blank."
    assert result.summary["page_count"] == 2


def test_extract_pdf_text_from_api_reports_retryable_failure():
    failed_book = {
        "id": 7,
        "original_filename": "corrupt.pdf",
        "content_type": "application/pdf",
        "file_size": 100,
        "uploaded_at": "2026-06-27T12:00:00Z",
        "upload_status": "uploaded",
        "processing_status": "extraction_failed",
        "error_message": "Text extraction failed. Retry extraction or upload a cleaner PDF.",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "detail": {
                    "message": failed_book["error_message"],
                    "retryable": True,
                    "book": failed_book,
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = extract_pdf_text_from_api("http://api.test", book_id=7, client=client)

    assert result.success is False
    assert result.message == "Text extraction failed. Retry extraction or upload a cleaner PDF."
    assert result.retryable is True
    assert result.book == failed_book


def test_detect_chapters_from_api_reports_book_map_summary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://api.test/books/7/chapter-detection"
        return httpx.Response(
            200,
            json={
                "book": {
                    "id": 7,
                    "original_filename": "learning.pdf",
                    "content_type": "application/pdf",
                    "file_size": 100,
                    "uploaded_at": "2026-06-27T12:00:00Z",
                    "upload_status": "uploaded",
                    "processing_status": "extracted",
                    "error_message": None,
                    "chapter_detection_status": "detected",
                    "chapter_detection_confidence": "high",
                    "chapter_detection_message": None,
                },
                "summary": {
                    "chapter_count": 2,
                    "confidence": "high",
                    "warning": None,
                },
                "chapters": [
                    {
                        "book_id": 7,
                        "chapter_number": 1,
                        "title": "Getting Started",
                        "start_page": 1,
                        "end_page": 3,
                        "start_source_location": "book:7:page:1",
                        "end_source_location": "book:7:page:3",
                        "confidence": "high",
                        "detection_source": "heading_pattern",
                    }
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = detect_chapters_from_api("http://api.test", book_id=7, client=client)

    assert result.success is True
    assert result.message == "Detected 2 chapters with high confidence."
    assert result.summary["chapter_count"] == 2
    assert result.chapters[0]["title"] == "Getting Started"
