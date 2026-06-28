from fastapi.testclient import TestClient

from smartread_api.main import create_app
from tests.pdf_fixtures import add_outline_to_pdf, build_pdf_with_text_pages


def test_detect_chapters_from_obvious_heading_patterns(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    pdf_bytes = build_pdf_with_text_pages(
        [
            "Chapter 1: Getting Started\nThe first chapter introduces the learning system.",
            "Chapter 2: Practicing Recall\nThe second chapter explains active recall.",
        ]
    )
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("chapters.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]
    client.post(f"/books/{book_id}/extraction")

    detection_response = client.post(f"/books/{book_id}/chapter-detection")

    assert detection_response.status_code == 200
    payload = detection_response.json()
    assert payload["book"]["chapter_detection_status"] == "detected"
    assert payload["summary"] == {
        "chapter_count": 2,
        "confidence": "high",
        "warning": None,
    }
    assert [
        {
            "chapter_number": chapter["chapter_number"],
            "title": chapter["title"],
            "start_page": chapter["start_page"],
            "end_page": chapter["end_page"],
            "start_source_location": chapter["start_source_location"],
            "end_source_location": chapter["end_source_location"],
            "confidence": chapter["confidence"],
        }
        for chapter in payload["chapters"]
    ] == [
        {
            "chapter_number": 1,
            "title": "Getting Started",
            "start_page": 1,
            "end_page": 1,
            "start_source_location": f"book:{book_id}:page:1",
            "end_source_location": f"book:{book_id}:page:1",
            "confidence": "high",
        },
        {
            "chapter_number": 2,
            "title": "Practicing Recall",
            "start_page": 2,
            "end_page": 2,
            "start_source_location": f"book:{book_id}:page:2",
            "end_source_location": f"book:{book_id}:page:2",
            "confidence": "high",
        },
    ]


def test_detect_chapters_from_weaker_numbered_headings_with_low_confidence(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    pdf_bytes = build_pdf_with_text_pages(
        [
            "1. Foundations\nThis section has a weaker heading.",
            "2. Practice Loops\nThis section also looks chapter-like.",
        ]
    )
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("weak-headings.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]
    client.post(f"/books/{book_id}/extraction")

    detection_response = client.post(f"/books/{book_id}/chapter-detection")

    assert detection_response.status_code == 200
    payload = detection_response.json()
    assert payload["book"]["chapter_detection_status"] == "detected"
    assert payload["summary"] == {
        "chapter_count": 2,
        "confidence": "low",
        "warning": "Chapter detection confidence is low. Review boundaries before generating lessons.",
    }
    assert [chapter["title"] for chapter in payload["chapters"]] == [
        "Foundations",
        "Practice Loops",
    ]
    assert {chapter["confidence"] for chapter in payload["chapters"]} == {"low"}


def test_detect_chapters_prefers_pdf_outline_when_available(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    pdf_without_headings = build_pdf_with_text_pages(
        [
            "The opening material starts without a visible heading.",
            "The first outlined chapter continues here.",
            "The second outlined chapter starts here.",
        ]
    )
    pdf_bytes = add_outline_to_pdf(
        pdf_without_headings,
        [
            ("Focus Systems", 1),
            ("Recall Practice", 3),
        ],
    )
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("outline.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]
    client.post(f"/books/{book_id}/extraction")

    detection_response = client.post(f"/books/{book_id}/chapter-detection")

    assert detection_response.status_code == 200
    chapters = detection_response.json()["chapters"]
    assert [chapter["title"] for chapter in chapters] == ["Focus Systems", "Recall Practice"]
    assert [(chapter["start_page"], chapter["end_page"]) for chapter in chapters] == [(1, 2), (3, 3)]
    assert {chapter["detection_source"] for chapter in chapters} == {"pdf_outline"}


def test_detected_chapters_survive_reload_and_retry_does_not_duplicate_records(tmp_path):
    database_path = tmp_path / "smartread.db"
    first_client = TestClient(create_app(database_path=database_path))
    pdf_bytes = build_pdf_with_text_pages(
        [
            "Chapter 1: Focus\nThe first chapter.",
            "Chapter 2: Recall\nThe second chapter.",
        ]
    )
    upload_response = first_client.post(
        "/books/uploads",
        files={"file": ("retry-chapters.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]
    first_client.post(f"/books/{book_id}/extraction")

    first_client.post(f"/books/{book_id}/chapter-detection")
    retry_response = first_client.post(f"/books/{book_id}/chapter-detection")
    reloaded_client = TestClient(create_app(database_path=database_path))
    chapters_response = reloaded_client.get(f"/books/{book_id}/chapters")

    assert retry_response.status_code == 200
    assert chapters_response.status_code == 200
    assert chapters_response.json()["chapters"] == retry_response.json()["chapters"]
    assert [chapter["chapter_number"] for chapter in chapters_response.json()["chapters"]] == [1, 2]


def test_no_detectable_chapters_returns_empty_manual_review_state(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    pdf_bytes = build_pdf_with_text_pages(
        [
            "This page has useful material but no visible chapter heading.",
            "This page continues the same continuous essay.",
        ]
    )
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("no-chapters.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]
    client.post(f"/books/{book_id}/extraction")

    detection_response = client.post(f"/books/{book_id}/chapter-detection")

    assert detection_response.status_code == 200
    payload = detection_response.json()
    assert payload["book"]["chapter_detection_status"] == "not_detected"
    assert payload["summary"] == {
        "chapter_count": 0,
        "confidence": "none",
        "warning": "No chapters could be detected. Manual chapter review will be required.",
    }
    assert payload["chapters"] == []
