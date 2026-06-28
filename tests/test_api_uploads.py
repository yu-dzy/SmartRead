from fastapi.testclient import TestClient

from smartread_api.main import create_app


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def test_upload_valid_pdf_creates_persisted_uploaded_book_metadata(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))

    response = client.post(
        "/books/uploads",
        files={"file": ("deep-work.pdf", PDF_BYTES, "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_filename"] == "deep-work.pdf"
    assert payload["content_type"] == "application/pdf"
    assert payload["file_size"] == len(PDF_BYTES)
    assert payload["upload_status"] == "uploaded"
    assert payload["processing_status"] == "not_started"
    assert payload["uploaded_at"].endswith("Z")


def test_uploaded_book_metadata_survives_app_reload(tmp_path):
    database_path = tmp_path / "smartread.db"
    first_client = TestClient(create_app(database_path=database_path))
    upload_response = first_client.post(
        "/books/uploads",
        files={"file": ("deep-work.pdf", PDF_BYTES, "application/pdf")},
    )

    reloaded_client = TestClient(create_app(database_path=database_path))
    response = reloaded_client.get("/books")

    assert response.status_code == 200
    assert response.json() == {"books": [upload_response.json()]}


def test_upload_rejects_unsupported_file_types_without_creating_a_book(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))

    response = client.post(
        "/books/uploads",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "SmartRead accepts PDF uploads only."
    assert client.get("/books").json() == {"books": []}


def test_unreadable_pdf_upload_is_retryable_without_duplicate_records(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))

    first_response = client.post(
        "/books/uploads",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    retry_response = client.post(
        "/books/uploads",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert first_response.status_code == 422
    assert retry_response.status_code == 422
    detail = retry_response.json()["detail"]
    assert detail["message"] == "The PDF could not be read. Upload a valid PDF and try again."
    assert detail["retryable"] is True
    assert detail["book"]["upload_status"] == "failed"
    assert detail["book"]["processing_status"] == "not_started"
    assert detail["book"]["error_message"] == detail["message"]
    assert client.get("/books").json()["books"] == [detail["book"]]


def test_malformed_pdf_upload_is_rejected_as_retryable(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))

    response = client.post(
        "/books/uploads",
        files={"file": ("broken.pdf", b"%PDF-1.4\nnot complete", "application/pdf")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "The PDF could not be read. Upload a valid PDF and try again."
    assert detail["retryable"] is True
    assert detail["book"]["original_filename"] == "broken.pdf"
    assert detail["book"]["upload_status"] == "failed"
