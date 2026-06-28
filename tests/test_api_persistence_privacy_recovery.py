import sqlite3
import re
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from smartread_api.chapter_summaries import ChapterSummaryGenerationError
from smartread_api.main import create_app
from tests.pdf_fixtures import build_pdf_with_text_pages


class FakeSummaryGenerator:
    provider = "test"
    model = "fake-summary"

    def generate_summary(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "central_argument": {
                "claim": "Focus improves when attention is protected from constant switching.",
                "citation_ids": ["sc1"],
            },
            "supporting_ideas": [
                {
                    "claim": "Protected attention makes deliberate practice easier to repeat.",
                    "citation_ids": ["sc2"],
                }
            ],
            "citations": [
                {
                    "id": "sc1",
                    "source_location": "book:1:page:1",
                    "page_number": 1,
                    "source_excerpt": (
                        "Focus improves when attention is protected from constant switching."
                    ),
                },
                {
                    "id": "sc2",
                    "source_location": "book:1:page:2",
                    "page_number": 2,
                    "source_excerpt": (
                        "Protected attention makes deliberate practice easier to repeat."
                    ),
                },
            ],
        }


class FlakySummaryGenerator(FakeSummaryGenerator):
    def __init__(self) -> None:
        self.calls = 0

    def generate_summary(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
    ) -> dict[str, object]:
        self.calls += 1
        if self.calls == 1:
            raise ChapterSummaryGenerationError("temporary summary failure")

        return super().generate_summary(chapter=chapter, pages=pages)


class FakeConceptsTakeawaysGenerator:
    provider = "test"
    model = "fake-concepts"

    def generate_concepts_takeaways(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
    ) -> dict[str, object]:
        return _valid_concepts_takeaways_output()


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
        return _valid_quiz_output()


def test_deleting_uploaded_book_removes_generated_learning_state_and_stale_access(tmp_path):
    database_path = tmp_path / "smartread.db"
    client = TestClient(_create_test_app(database_path))
    book_id = _create_full_learning_state(client)

    response = client.delete(f"/books/{book_id}")

    assert response.status_code == 200
    assert response.json() == {
        "deleted": True,
        "book_id": book_id,
        "message": "Uploaded Book and related learning data were deleted.",
    }
    assert client.get("/books").json()["books"] == []
    for method, path in [
        ("get", f"/books/{book_id}/pages"),
        ("get", f"/books/{book_id}/chapters"),
        ("get", f"/books/{book_id}/chapter-boundaries"),
        ("get", f"/books/{book_id}/chapter-boundaries/1/source-pages"),
        ("get", f"/books/{book_id}/chapter-boundaries/1/summary"),
        ("get", f"/books/{book_id}/chapter-boundaries/1/summary/citations/sc1/evidence"),
        ("get", f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways"),
        ("get", f"/books/{book_id}/chapter-boundaries/1/quiz"),
        ("get", f"/books/{book_id}/chapter-boundaries/1/quiz/progress"),
        ("get", f"/books/{book_id}/chapter-boundaries/1/missed-concepts"),
        ("get", f"/books/{book_id}/chapter-boundaries/1/review-items"),
        ("post", f"/books/{book_id}/chapter-boundaries/1/review-items/1/answer"),
    ]:
        if method == "post":
            stale_response = client.post(path, json={"selected_answer": "Constant switching"})
        else:
            stale_response = client.get(path)
        assert stale_response.status_code == 404


def test_uploaded_book_and_learning_data_are_isolated_by_owner_identifier(tmp_path):
    database_path = tmp_path / "smartread.db"
    client = TestClient(_create_test_app(database_path))
    alice_headers = {"X-SmartRead-Owner": "alice"}
    bob_headers = {"X-SmartRead-Owner": "bob"}
    book_id = _create_full_learning_state(client, headers=alice_headers)

    alice_books = client.get("/books", headers=alice_headers)
    bob_books = client.get("/books", headers=bob_headers)
    bob_pages = client.get(f"/books/{book_id}/pages", headers=bob_headers)
    bob_summary = client.get(
        f"/books/{book_id}/chapter-boundaries/1/summary",
        headers=bob_headers,
    )
    bob_review_items = client.get(
        f"/books/{book_id}/chapter-boundaries/1/review-items",
        headers=bob_headers,
    )

    assert alice_books.status_code == 200
    assert [book["id"] for book in alice_books.json()["books"]] == [book_id]
    assert bob_books.status_code == 200
    assert bob_books.json()["books"] == []
    assert bob_pages.status_code == 404
    assert bob_summary.status_code == 404
    assert bob_review_items.status_code == 404


def test_migrated_upload_uniqueness_keeps_separate_owner_records(tmp_path):
    database_path = tmp_path / "smartread.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE uploaded_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                content_sha256 TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                upload_status TEXT NOT NULL,
                processing_status TEXT NOT NULL,
                error_message TEXT,
                pdf_content BLOB,
                chapter_detection_status TEXT NOT NULL DEFAULT 'not_started',
                chapter_detection_confidence TEXT,
                chapter_detection_message TEXT,
                chapter_review_status TEXT NOT NULL DEFAULT 'not_started',
                UNIQUE(original_filename, file_size, content_sha256)
            )
            """
        )
    client = TestClient(_create_test_app(database_path))
    pdf_bytes = build_pdf_with_text_pages(["Chapter 1: Focus\nOwner isolation matters."])

    alice_upload = client.post(
        "/books/uploads",
        headers={"X-SmartRead-Owner": "alice"},
        files={"file": ("same.pdf", pdf_bytes, "application/pdf")},
    )
    bob_upload = client.post(
        "/books/uploads",
        headers={"X-SmartRead-Owner": "bob"},
        files={"file": ("same.pdf", pdf_bytes, "application/pdf")},
    )

    assert alice_upload.status_code == 201
    assert bob_upload.status_code == 201
    assert alice_upload.json()["id"] != bob_upload.json()["id"]
    assert [
        book["id"]
        for book in client.get("/books", headers={"X-SmartRead-Owner": "alice"}).json()["books"]
    ] == [alice_upload.json()["id"]]
    assert [
        book["id"]
        for book in client.get("/books", headers={"X-SmartRead-Owner": "bob"}).json()["books"]
    ] == [bob_upload.json()["id"]]


def test_full_learning_state_survives_backend_restart(tmp_path):
    database_path = tmp_path / "smartread.db"
    client = TestClient(_create_test_app(database_path))
    book_id = _create_full_learning_state(client)

    reloaded_client = TestClient(_create_test_app(database_path))

    books = reloaded_client.get("/books")
    pages = reloaded_client.get(f"/books/{book_id}/pages")
    detected_chapters = reloaded_client.get(f"/books/{book_id}/chapters")
    accepted_chapters = reloaded_client.get(f"/books/{book_id}/chapter-boundaries")
    chapter_source = reloaded_client.get(f"/books/{book_id}/chapter-boundaries/1/source-pages")
    summary = reloaded_client.get(f"/books/{book_id}/chapter-boundaries/1/summary")
    evidence = reloaded_client.get(
        f"/books/{book_id}/chapter-boundaries/1/summary/citations/sc1/evidence"
    )
    concepts_takeaways = reloaded_client.get(
        f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways"
    )
    quiz = reloaded_client.get(f"/books/{book_id}/chapter-boundaries/1/quiz")
    progress = reloaded_client.get(f"/books/{book_id}/chapter-boundaries/1/quiz/progress")
    missed_concepts = reloaded_client.get(
        f"/books/{book_id}/chapter-boundaries/1/missed-concepts"
    )
    review_items = reloaded_client.get(f"/books/{book_id}/chapter-boundaries/1/review-items")

    assert books.status_code == 200
    assert books.json()["books"][0]["id"] == book_id
    assert books.json()["books"][0]["original_filename"] == "privacy.pdf"
    assert [page["page_number"] for page in pages.json()["pages"]] == [1, 2, 3]
    assert pages.json()["pages"][0]["source_location"] == f"book:{book_id}:page:1"
    assert detected_chapters.json()["chapters"][0]["title"] == "Focus"
    assert accepted_chapters.json()["chapters"][0]["review_status"] == "accepted"
    assert chapter_source.json()["chapter"]["title"] == "Focus"
    assert summary.json()["summary"]["central_argument"]["citation_ids"] == ["sc1"]
    assert evidence.json()["verification_status"] == "verified"
    assert evidence.json()["source_excerpt"] == (
        "Focus improves when attention is protected from constant switching."
    )
    assert concepts_takeaways.json()["content"]["core_concepts"][0]["name"] == (
        "Protected Attention"
    )
    assert concepts_takeaways.json()["content"]["key_takeaways"][0]["citation_ids"] == ["c1"]
    assert len(quiz.json()["quiz"]["questions"]) == 5
    assert progress.json()["progress"] == {
        "answered_count": 1,
        "correct_count": 0,
        "incorrect_count": 1,
        "total_questions": 5,
    }
    assert progress.json()["answers"][0]["selected_answer"] == "Long-term memory"
    assert missed_concepts.json()["missed_concepts"][0]["concept_name"] == (
        "Protected Attention"
    )
    assert review_items.json()["upcoming_review_items"][0]["stage"] == "day_1"
    assert review_items.json()["upcoming_review_items"][0]["due_on"] == "2026-06-29"


def test_review_queue_recovers_missing_review_item_after_partial_failure(tmp_path):
    database_path = tmp_path / "smartread.db"
    client = TestClient(_create_test_app(database_path))
    book_id = _create_full_learning_state(client)
    with sqlite3.connect(database_path) as connection:
        connection.execute("DELETE FROM review_results")
        connection.execute("DELETE FROM review_items")

    response = client.get(f"/books/{book_id}/chapter-boundaries/1/review-items")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {"due_review_count": 0, "active_review_count": 1}
    assert payload["upcoming_review_items"][0]["concept_name"] == "Protected Attention"
    assert payload["upcoming_review_items"][0]["due_on"] == "2026-06-29"
    second_response = client.get(f"/books/{book_id}/chapter-boundaries/1/review-items")
    assert len(second_response.json()["upcoming_review_items"]) == 1


def test_failed_summary_generation_can_be_retried_without_duplicate_state(tmp_path):
    database_path = tmp_path / "smartread.db"
    summary_generator = FlakySummaryGenerator()
    client = TestClient(
        create_app(
            database_path=database_path,
            summary_generator=summary_generator,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=FakeQuizGenerator(),
            clock=lambda: datetime(2026, 6, 28, 9, 0, tzinfo=UTC),
        )
    )
    book_id = _upload_extract_and_accept_chapters(client)

    failed_response = client.post(f"/books/{book_id}/chapter-boundaries/1/summary")
    retry_response = client.post(f"/books/{book_id}/chapter-boundaries/1/summary")
    persisted_response = client.get(f"/books/{book_id}/chapter-boundaries/1/summary")

    assert failed_response.status_code == 422
    assert failed_response.json()["detail"]["retryable"] is True
    assert failed_response.json()["detail"]["summary"]["generation_status"] == "failed"
    assert retry_response.status_code == 200
    assert persisted_response.status_code == 200
    assert persisted_response.json()["generation_status"] == "generated"
    assert persisted_response.json()["generation_error"] is None
    assert persisted_response.json()["summary"]["central_argument"]["claim"] == (
        "Focus improves when attention is protected from constant switching."
    )


def test_invalid_upload_retry_reuses_failed_book_record(tmp_path):
    client = TestClient(_create_test_app(tmp_path / "smartread.db"))
    invalid_pdf = b"%PDF-1.4\nmissing eof marker"

    first_response = client.post(
        "/books/uploads",
        files={"file": ("broken.pdf", invalid_pdf, "application/pdf")},
    )
    second_response = client.post(
        "/books/uploads",
        files={"file": ("broken.pdf", invalid_pdf, "application/pdf")},
    )

    assert first_response.status_code == 422
    assert second_response.status_code == 422
    assert first_response.json()["detail"]["book"]["id"] == second_response.json()["detail"][
        "book"
    ]["id"]
    assert len(client.get("/books").json()["books"]) == 1


def test_citation_evidence_exposes_focused_excerpt_not_complete_page_text(tmp_path):
    client = TestClient(_create_test_app(tmp_path / "smartread.db"))
    book_id = _create_full_learning_state(client)

    response = client.get(
        f"/books/{book_id}/chapter-boundaries/1/summary/citations/sc1/evidence"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_excerpt"] == (
        "Focus improves when attention is protected from constant switching."
    )
    assert "Chapter 1: Focus" not in payload["source_excerpt"]
    assert "Deep focus protects attention" not in payload["source_excerpt"]


def test_runtime_data_and_secret_files_are_gitignored():
    root = Path(__file__).parents[1]
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")

    assert ".smartread/" in gitignore
    assert ".env" in gitignore
    assert ".streamlit/secrets.toml" in gitignore


def test_source_files_do_not_contain_committed_api_keys_or_secrets():
    root = Path(__file__).parents[1]
    scanned_suffixes = {".md", ".py", ".toml", ".txt", ".json"}
    forbidden_patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"OPENAI_API_KEY\s*=\s*['\"]sk-[A-Za-z0-9_-]{20,}['\"]"),
        re.compile("your-real" + "-api-key"),
    ]

    for path in root.rglob("*"):
        if (
            path.is_dir()
            or path.suffix not in scanned_suffixes
            or ".git" in path.parts
            or ".venv" in path.parts
            or ".smartread" in path.parts
        ):
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern.search(text) is None, f"{pattern.pattern!r} found in {path}"


def _create_test_app(database_path: object):
    return create_app(
        database_path=database_path,
        summary_generator=FakeSummaryGenerator(),
        concepts_generator=FakeConceptsTakeawaysGenerator(),
        quiz_generator=FakeQuizGenerator(),
        clock=lambda: datetime(2026, 6, 28, 9, 0, tzinfo=UTC),
    )


def _create_full_learning_state(
    client: TestClient,
    *,
    headers: dict[str, str] | None = None,
) -> int:
    book_id = _upload_extract_and_accept_chapters(client, headers=headers)
    request_headers = headers or {}
    client.post(f"/books/{book_id}/chapter-boundaries/1/summary", headers=request_headers)
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways",
        headers=request_headers,
    )
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz", headers=request_headers)
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        headers=request_headers,
        json={"selected_answer": "Long-term memory"},
    )
    return book_id


def _upload_extract_and_accept_chapters(
    client: TestClient,
    *,
    headers: dict[str, str] | None = None,
) -> int:
    request_headers = headers or {}
    pdf_bytes = build_pdf_with_text_pages(
        [
            (
                "Chapter 1: Focus\n"
                "Focus improves when attention is protected from constant switching. "
                "Deep focus protects attention from constant switching so learners can "
                "practice deliberately."
            ),
            (
                "Protected attention makes deliberate practice easier to repeat. "
                "Retrieval cues help learners recall ideas later and connect practice to "
                "long term memory. A protected block reduces context switching and makes "
                "deliberate practice easier to repeat."
            ),
            "Chapter 2: Systems\nSimple systems make review easier.",
        ]
    )
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("privacy.pdf", pdf_bytes, "application/pdf")},
        headers=request_headers,
    )
    book_id = upload_response.json()["id"]
    client.post(f"/books/{book_id}/extraction", headers=request_headers)
    client.post(f"/books/{book_id}/chapter-detection", headers=request_headers)
    client.put(
        f"/books/{book_id}/chapter-boundaries",
        headers=request_headers,
        json={
            "chapters": [
                {"chapter_number": 1, "title": "Focus", "start_page": 1, "end_page": 2},
                {"chapter_number": 2, "title": "Systems", "start_page": 3, "end_page": 3},
            ]
        },
    )
    return book_id


def _valid_concepts_takeaways_output() -> dict[str, object]:
    return {
        "core_concepts": [
            {
                "name": "Protected Attention",
                "explanation": (
                    "Protected attention reduces constant switching so learners can practice "
                    "deliberately."
                ),
                "why_it_matters": (
                    "It matters because deliberate practice becomes easier when attention stays "
                    "protected."
                ),
                "example": "A learner blocks messages before reading a difficult chapter.",
                "citation_ids": ["c1"],
            },
            {
                "name": "Retrieval Cues",
                "explanation": "Retrieval cues help learners recall ideas later.",
                "why_it_matters": "They matter because cues connect practice to long term memory.",
                "example": "A learner writes a short cue after finishing a chapter.",
                "citation_ids": ["c2"],
            }
        ],
        "key_takeaways": [
            {
                "text": "Protecting attention makes deliberate practice easier.",
                "citation_ids": ["c1"],
            },
            {
                "text": "Retrieval cues help learners recall and connect ideas later.",
                "citation_ids": ["c2"],
            },
        ],
        "citations": [
            {
                "id": "c1",
                "source_location": "book:1:page:1",
                "page_number": 1,
                "source_excerpt": (
                    "Deep focus protects attention from constant switching so learners can "
                    "practice deliberately."
                ),
            },
            {
                "id": "c2",
                "source_location": "book:1:page:2",
                "page_number": 2,
                "source_excerpt": (
                    "Retrieval cues help learners recall ideas later and connect practice to "
                    "long term memory."
                ),
            },
        ],
    }


def _valid_quiz_output() -> dict[str, object]:
    return {
        "questions": [
            {
                "id": "q1",
                "question_text": "What does protected attention reduce during deliberate practice?",
                "question_type": "multiple_choice",
                "answer_options": [
                    "Constant switching",
                    "Long-term memory",
                    "Chapter boundaries",
                    "Source citations",
                ],
                "correct_answer": "Constant switching",
                "explanation": (
                    "Protected attention reduces constant switching so deliberate practice is "
                    "easier to repeat."
                ),
                "tested_concept": "Protected Attention",
                "citation_id": "qc1",
            },
            {
                "id": "q2",
                "question_text": "True or false: retrieval cues help recall ideas later.",
                "question_type": "true_false",
                "answer_options": ["True", "False"],
                "correct_answer": "True",
                "explanation": "Retrieval cues help learners recall ideas later.",
                "tested_concept": "Retrieval Cues",
                "citation_id": "qc2",
            },
            {
                "id": "q3",
                "question_text": (
                    "A learner silences chat before reading a hard chapter. Which concept "
                    "does this apply?"
                ),
                "question_type": "scenario_application",
                "answer_options": [
                    "Protected Attention",
                    "Retrieval Cues",
                    "Public Redistribution",
                    "Chapter Detection",
                ],
                "correct_answer": "Protected Attention",
                "explanation": "Blocking messages protects attention from constant switching.",
                "tested_concept": "Protected Attention",
                "citation_id": "qc1",
            },
            {
                "id": "q4",
                "question_text": "Which practice helps connect ideas to long term memory?",
                "question_type": "multiple_choice",
                "answer_options": [
                    "Using retrieval cues",
                    "Skipping feedback",
                    "Ignoring source excerpts",
                    "Changing page numbers",
                ],
                "correct_answer": "Using retrieval cues",
                "explanation": "Retrieval cues connect practice to long term memory.",
                "tested_concept": "Retrieval Cues",
                "citation_id": "qc2",
            },
            {
                "id": "q5",
                "question_text": "What makes deliberate practice easier to repeat?",
                "question_type": "multiple_choice",
                "answer_options": [
                    "Reducing context switching",
                    "Generating whole-book lessons",
                    "Avoiding active recall",
                    "Removing citations",
                ],
                "correct_answer": "Reducing context switching",
                "explanation": (
                    "A protected block reduces context switching and makes deliberate practice "
                    "easier to repeat."
                ),
                "tested_concept": "Protected Attention",
                "citation_id": "qc3",
            },
        ],
        "citations": [
            {
                "id": "qc1",
                "source_location": "book:1:page:1",
                "page_number": 1,
                "source_excerpt": (
                    "Deep focus protects attention from constant switching so learners can "
                    "practice deliberately."
                ),
            },
            {
                "id": "qc2",
                "source_location": "book:1:page:2",
                "page_number": 2,
                "source_excerpt": (
                    "Retrieval cues help learners recall ideas later and connect practice to "
                    "long term memory."
                ),
            },
            {
                "id": "qc3",
                "source_location": "book:1:page:2",
                "page_number": 2,
                "source_excerpt": (
                    "A protected block reduces context switching and makes deliberate practice "
                    "easier to repeat."
                ),
            },
        ],
    }
