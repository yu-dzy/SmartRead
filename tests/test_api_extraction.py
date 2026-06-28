from fastapi.testclient import TestClient

from smartread_api.main import create_app
from tests.pdf_fixtures import build_pdf_with_text_pages


def test_extract_pdf_text_persists_pages_with_source_locations(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    pdf_bytes = build_pdf_with_text_pages(["First page alpha", "Second page beta"])
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("learning.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]

    extraction_response = client.post(f"/books/{book_id}/extraction")

    assert extraction_response.status_code == 200
    payload = extraction_response.json()
    assert payload["book"]["processing_status"] == "extracted"
    assert payload["summary"] == {
        "page_count": 2,
        "text_page_count": 2,
        "blank_page_count": 0,
    }
    assert payload["pages"] == [
        {
            "book_id": book_id,
            "page_number": 1,
            "source_location": f"book:{book_id}:page:1",
            "extracted_text": "First page alpha",
        },
        {
            "book_id": book_id,
            "page_number": 2,
            "source_location": f"book:{book_id}:page:2",
            "extracted_text": "Second page beta",
        },
    ]


def test_extract_pdf_text_preserves_blank_pages_and_page_numbers(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    pdf_bytes = build_pdf_with_text_pages(["Readable intro", "", "After the blank"])
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("with-blank.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]

    extraction_response = client.post(f"/books/{book_id}/extraction")

    assert extraction_response.status_code == 200
    payload = extraction_response.json()
    assert payload["summary"] == {
        "page_count": 3,
        "text_page_count": 2,
        "blank_page_count": 1,
    }
    assert [page["page_number"] for page in payload["pages"]] == [1, 2, 3]
    assert payload["pages"][1] == {
        "book_id": book_id,
        "page_number": 2,
        "source_location": f"book:{book_id}:page:2",
        "extracted_text": "",
    }


def test_extracted_pages_survive_reload_and_extraction_retry_does_not_duplicate_pages(tmp_path):
    database_path = tmp_path / "smartread.db"
    first_client = TestClient(create_app(database_path=database_path))
    pdf_bytes = build_pdf_with_text_pages(["First page", "Second page"])
    upload_response = first_client.post(
        "/books/uploads",
        files={"file": ("retry.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]

    first_client.post(f"/books/{book_id}/extraction")
    retry_response = first_client.post(f"/books/{book_id}/extraction")
    reloaded_client = TestClient(create_app(database_path=database_path))
    pages_response = reloaded_client.get(f"/books/{book_id}/pages")

    assert retry_response.status_code == 200
    assert pages_response.status_code == 200
    assert pages_response.json()["pages"] == retry_response.json()["pages"]
    assert [page["page_number"] for page in pages_response.json()["pages"]] == [1, 2]


def test_extraction_failure_sets_retryable_error_state_without_pages(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    corrupt_pdf = b"%PDF-1.4\nnot a parseable pdf body\n%%EOF\n"
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("corrupt.pdf", corrupt_pdf, "application/pdf")},
    )
    book_id = upload_response.json()["id"]

    extraction_response = client.post(f"/books/{book_id}/extraction")
    pages_response = client.get(f"/books/{book_id}/pages")

    assert extraction_response.status_code == 422
    detail = extraction_response.json()["detail"]
    assert detail["message"] == "Text extraction failed. Retry extraction or upload a cleaner PDF."
    assert detail["retryable"] is True
    assert detail["book"]["processing_status"] == "extraction_failed"
    assert detail["book"]["error_message"] == detail["message"]
    assert pages_response.json() == {"pages": []}
