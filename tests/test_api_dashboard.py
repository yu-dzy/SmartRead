from datetime import UTC, datetime

from fastapi.testclient import TestClient

from smartread_api.main import create_app
from tests.pdf_fixtures import build_pdf_with_text_pages


class FakeConceptsTakeawaysGenerator:
    provider = "test"
    model = "fake-concepts"

    def generate_concepts_takeaways(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "core_concepts": [
                {
                    "name": "Protected Attention",
                    "explanation": "Protected attention reduces constant switching.",
                    "why_it_matters": "It makes deliberate practice easier.",
                    "example": "A learner silences notifications before reading.",
                    "citation_ids": ["c1"],
                }
            ],
            "key_takeaways": [
                {
                    "text": "Protecting attention makes deliberate practice easier.",
                    "citation_ids": ["c1"],
                }
            ],
            "citations": [
                {
                    "id": "c1",
                    "source_location": "book:1:page:1",
                    "page_number": 1,
                    "source_excerpt": (
                        "Protected attention reduces constant switching. It makes deliberate "
                        "practice easier. Protecting attention makes deliberate practice easier."
                    ),
                }
            ],
        }


class FakeQuizGenerator:
    provider = "test"
    model = "fake-quiz"

    def generate_quiz(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
        core_concepts: list[dict[str, object]],
    ) -> dict[str, object]:
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
                    "question_text": "True or false: focus is protected by switching tasks.",
                    "question_type": "true_false",
                    "answer_options": ["True", "False"],
                    "correct_answer": "False",
                    "explanation": "The chapter says attention is protected from switching.",
                    "tested_concept": "Protected Attention",
                    "citation_id": "qc1",
                },
                {
                    "id": "q3",
                    "question_text": "Which habit applies protected attention?",
                    "question_type": "scenario_application",
                    "answer_options": ["Silencing notifications", "Opening more tabs"],
                    "correct_answer": "Silencing notifications",
                    "explanation": "Silencing notifications protects attention.",
                    "tested_concept": "Protected Attention",
                    "citation_id": "qc1",
                },
                {
                    "id": "q4",
                    "question_text": "What gets easier with protected attention?",
                    "question_type": "multiple_choice",
                    "answer_options": ["Deliberate practice", "Skipping feedback"],
                    "correct_answer": "Deliberate practice",
                    "explanation": "Protected attention makes deliberate practice easier.",
                    "tested_concept": "Protected Attention",
                    "citation_id": "qc2",
                },
                {
                    "id": "q5",
                    "question_text": "What should a learner reduce?",
                    "question_type": "multiple_choice",
                    "answer_options": ["Context switching", "Source citations"],
                    "correct_answer": "Context switching",
                    "explanation": "Reducing context switching supports protected attention.",
                    "tested_concept": "Protected Attention",
                    "citation_id": "qc2",
                },
            ],
            "citations": [
                {
                    "id": "qc1",
                    "source_location": "book:1:page:1",
                    "page_number": 1,
                    "source_excerpt": "Focus improves when attention is protected.",
                },
                {
                    "id": "qc2",
                    "source_location": "book:1:page:2",
                    "page_number": 2,
                    "source_excerpt": "Protected attention makes deliberate practice easier.",
                },
            ],
        }


def test_my_books_dashboard_returns_empty_book_list(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))

    response = client.get("/dashboard/books")

    assert response.status_code == 200
    assert response.json() == {"books": []}


def test_my_books_dashboard_shows_uploaded_book_status(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    pdf_bytes = build_pdf_with_text_pages(["Chapter 1: Focus\nA private book."])
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("deep-work.pdf", pdf_bytes, "application/pdf")},
    )

    response = client.get("/dashboard/books")

    assert response.status_code == 200
    assert response.json() == {
        "books": [
            {
                "id": upload_response.json()["id"],
                "title": "deep-work",
                "author": None,
                "original_filename": "deep-work.pdf",
                "upload_status": "uploaded",
                "analysis_status": "not_started",
                "completed_chapter_count": 0,
                "total_chapter_count": 0,
                "latest_quiz_performance": None,
                "chapter_mastery": {
                    "mastered_chapter_count": 0,
                    "chapter_count": 0,
                    "mastery_percent": 0,
                },
                "due_review_count": 0,
                "continue_target": None,
            }
        ]
    }


def test_my_books_dashboard_continue_targets_first_accepted_unfinished_chapter(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    book_id = _upload_extract_and_accept_chapters(client)

    response = client.get("/dashboard/books")

    assert response.status_code == 200
    book = response.json()["books"][0]
    assert book["analysis_status"] == "chapters_accepted"
    assert book["completed_chapter_count"] == 0
    assert book["total_chapter_count"] == 2
    assert book["continue_target"] == {
        "type": "chapter",
        "book_id": book_id,
        "chapter_number": 1,
        "tab": "Summary",
        "label": "Continue Chapter 1: Focus",
    }


def test_my_books_dashboard_shows_quiz_performance_and_next_unfinished_chapter(tmp_path):
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=FakeQuizGenerator(),
        )
    )
    book_id = _upload_extract_and_accept_chapters(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")
    for question_id, selected_answer in [
        ("q1", "Constant switching"),
        ("q2", "True"),
        ("q3", "Silencing notifications"),
        ("q4", "Deliberate practice"),
        ("q5", "Context switching"),
    ]:
        client.post(
            f"/books/{book_id}/chapter-boundaries/1/quiz/answers/{question_id}",
            json={"selected_answer": selected_answer},
        )

    response = client.get("/dashboard/books")

    assert response.status_code == 200
    book = response.json()["books"][0]
    assert book["completed_chapter_count"] == 1
    assert book["total_chapter_count"] == 2
    assert book["latest_quiz_performance"] == {
        "chapter_number": 1,
        "answered_count": 5,
        "correct_count": 4,
        "incorrect_count": 1,
        "total_questions": 5,
        "score_percent": 80,
    }
    assert book["chapter_mastery"] == {
        "mastered_chapter_count": 0,
        "chapter_count": 2,
        "mastery_percent": 80,
    }
    assert book["continue_target"] == {
        "type": "chapter",
        "book_id": book_id,
        "chapter_number": 2,
        "tab": "Summary",
        "label": "Continue Chapter 2: Systems",
    }


def test_my_books_dashboard_continue_prioritizes_due_review_after_restart(tmp_path):
    database_path = tmp_path / "smartread.db"
    client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=FakeQuizGenerator(),
            clock=lambda: datetime(2026, 6, 28, 9, 0, tzinfo=UTC),
        )
    )
    book_id = _upload_extract_and_accept_chapters(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Long-term memory"},
    )
    reloaded_client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=FakeQuizGenerator(),
            clock=lambda: datetime(2026, 6, 30, 9, 0, tzinfo=UTC),
        )
    )

    response = reloaded_client.get("/dashboard/books")

    assert response.status_code == 200
    book = response.json()["books"][0]
    assert book["due_review_count"] == 1
    assert book["continue_target"] == {
        "type": "due_review",
        "book_id": book_id,
        "chapter_number": 1,
        "review_item_id": 1,
        "tab": "Review",
        "label": "Review Protected Attention",
    }


def test_my_books_dashboard_is_scoped_to_current_owner(tmp_path):
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    pdf_bytes = build_pdf_with_text_pages(["Chapter 1: Focus\nA private owner book."])
    upload_response = client.post(
        "/books/uploads",
        headers={"X-SmartRead-Owner": "alice"},
        files={"file": ("alice-book.pdf", pdf_bytes, "application/pdf")},
    )

    alice_response = client.get("/dashboard/books", headers={"X-SmartRead-Owner": "alice"})
    bob_response = client.get("/dashboard/books", headers={"X-SmartRead-Owner": "bob"})

    assert alice_response.status_code == 200
    assert [book["id"] for book in alice_response.json()["books"]] == [
        upload_response.json()["id"]
    ]
    assert bob_response.status_code == 200
    assert bob_response.json() == {"books": []}


def _upload_extract_and_accept_chapters(client: TestClient) -> int:
    pdf_bytes = build_pdf_with_text_pages(
        [
            (
                "Chapter 1: Focus\n"
                "Focus improves when attention is protected. Protected attention reduces "
                "constant switching. It makes deliberate practice easier. Protecting attention "
                "makes deliberate practice easier."
            ),
            "Protected attention makes deliberate practice easier.",
            "Chapter 2: Systems\nSimple systems make review easier.",
        ]
    )
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("learning.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]
    client.post(f"/books/{book_id}/extraction")
    client.post(f"/books/{book_id}/chapter-detection")
    client.put(
        f"/books/{book_id}/chapter-boundaries",
        json={
            "chapters": [
                {"chapter_number": 1, "title": "Focus", "start_page": 1, "end_page": 2},
                {"chapter_number": 2, "title": "Systems", "start_page": 3, "end_page": 3},
            ]
        },
    )
    return book_id
