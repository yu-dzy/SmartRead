from fastapi.testclient import TestClient

from smartread_api.main import create_app
from tests.pdf_fixtures import build_pdf_with_text_pages


def test_accept_detected_chapter_boundaries_persists_accepted_chapters(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    book_id = _upload_extract_and_detect_chapters(client)

    response = client.put(
        f"/books/{book_id}/chapter-boundaries",
        json={
            "chapters": [
                {"chapter_number": 1, "title": "Focus", "start_page": 1, "end_page": 1},
                {"chapter_number": 2, "title": "Recall", "start_page": 2, "end_page": 2},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["book"]["chapter_review_status"] == "accepted"
    assert payload["chapters"] == [
        {
            "book_id": book_id,
            "chapter_number": 1,
            "title": "Focus",
            "start_page": 1,
            "end_page": 1,
            "start_source_location": f"book:{book_id}:page:1",
            "end_source_location": f"book:{book_id}:page:1",
            "review_status": "accepted",
        },
        {
            "book_id": book_id,
            "chapter_number": 2,
            "title": "Recall",
            "start_page": 2,
            "end_page": 2,
            "start_source_location": f"book:{book_id}:page:2",
            "end_source_location": f"book:{book_id}:page:2",
            "review_status": "accepted",
        },
    ]


def test_rename_and_adjust_chapter_boundary_persists_as_accepted_boundary(tmp_path):
    database_path = tmp_path / "smartread.db"
    client = TestClient(create_app(database_path=database_path))
    book_id = _upload_extract_and_detect_chapters(client)

    save_response = client.put(
        f"/books/{book_id}/chapter-boundaries",
        json={
            "chapters": [
                {"chapter_number": 1, "title": "Deep Focus", "start_page": 1, "end_page": 2},
            ]
        },
    )
    reloaded_client = TestClient(create_app(database_path=database_path))
    get_response = reloaded_client.get(f"/books/{book_id}/chapter-boundaries")

    assert save_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["chapters"] == [
        {
            "book_id": book_id,
            "chapter_number": 1,
            "title": "Deep Focus",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": f"book:{book_id}:page:1",
            "end_source_location": f"book:{book_id}:page:2",
            "review_status": "accepted",
        }
    ]


def test_overlapping_chapter_boundaries_are_rejected_with_clear_error(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    book_id = _upload_extract_and_detect_chapters(client)

    response = client.put(
        f"/books/{book_id}/chapter-boundaries",
        json={
            "chapters": [
                {"chapter_number": 1, "title": "Focus", "start_page": 1, "end_page": 2},
                {"chapter_number": 2, "title": "Recall", "start_page": 2, "end_page": 2},
            ]
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Accepted chapter boundaries cannot overlap."
    assert client.get(f"/books/{book_id}/chapter-boundaries").json() == {"chapters": []}


def test_impossible_chapter_boundary_is_rejected_with_clear_error(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    book_id = _upload_extract_and_detect_chapters(client)

    response = client.put(
        f"/books/{book_id}/chapter-boundaries",
        json={
            "chapters": [
                {"chapter_number": 1, "title": "Focus", "start_page": 2, "end_page": 1},
            ]
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Chapter start page must be before its end page."


def test_downstream_source_selection_uses_accepted_boundaries_not_detected_guesses(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    book_id = _upload_extract_and_detect_three_page_book(client)
    client.put(
        f"/books/{book_id}/chapter-boundaries",
        json={
            "chapters": [
                {
                    "chapter_number": 1,
                    "title": "Corrected Focus",
                    "start_page": 1,
                    "end_page": 2,
                },
                {
                    "chapter_number": 2,
                    "title": "Recall",
                    "start_page": 3,
                    "end_page": 3,
                },
            ]
        },
    )

    response = client.get(f"/books/{book_id}/chapter-boundaries/1/source-pages")

    assert response.status_code == 200
    payload = response.json()
    assert payload["chapter"]["title"] == "Corrected Focus"
    assert payload["chapter"]["start_page"] == 1
    assert payload["chapter"]["end_page"] == 2
    assert [page["page_number"] for page in payload["pages"]] == [1, 2]
    assert payload["pages"][1]["extracted_text"] == "Extra focus practice"


def test_split_chapter_section_persists_multiple_accepted_boundaries(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    book_id = _upload_extract_and_detect_three_page_book(client)

    response = client.put(
        f"/books/{book_id}/chapter-boundaries",
        json={
            "chapters": [
                {"chapter_number": 1, "title": "Focus Setup", "start_page": 1, "end_page": 1},
                {"chapter_number": 2, "title": "Focus Practice", "start_page": 2, "end_page": 2},
                {"chapter_number": 3, "title": "Recall", "start_page": 3, "end_page": 3},
            ]
        },
    )

    assert response.status_code == 200
    assert [(chapter["title"], chapter["start_page"], chapter["end_page"]) for chapter in response.json()["chapters"]] == [
        ("Focus Setup", 1, 1),
        ("Focus Practice", 2, 2),
        ("Recall", 3, 3),
    ]


def _upload_extract_and_detect_chapters(client: TestClient) -> int:
    pdf_bytes = build_pdf_with_text_pages(
        [
            "Chapter 1: Focus\nThe first chapter.",
            "Chapter 2: Recall\nThe second chapter.",
        ]
    )
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("review.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]
    client.post(f"/books/{book_id}/extraction")
    client.post(f"/books/{book_id}/chapter-detection")
    return book_id


def _upload_extract_and_detect_three_page_book(client: TestClient) -> int:
    pdf_bytes = build_pdf_with_text_pages(
        [
            "Chapter 1: Focus\nThe first chapter.",
            "Extra focus practice",
            "Chapter 2: Recall\nThe second chapter.",
        ]
    )
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("three-page-review.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]
    client.post(f"/books/{book_id}/extraction")
    client.post(f"/books/{book_id}/chapter-detection")
    return book_id
