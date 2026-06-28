import httpx

from smartread_frontend.uploads import get_uploaded_books, upload_pdf_to_api


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
