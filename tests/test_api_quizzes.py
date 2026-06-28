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
        return _valid_concepts_takeaways_output()


class FakeQuizGenerator:
    provider = "test"
    model = "fake-quiz"

    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.calls: list[dict[str, object]] = []

    def generate_quiz(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
        core_concepts: list[dict[str, object]],
    ) -> dict[str, object]:
        self.calls.append(
            {
                "chapter": chapter,
                "pages": pages,
                "core_concepts": core_concepts,
            }
        )
        return self.output


def test_generate_five_grounded_quiz_questions_for_one_accepted_chapter(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    database_path = tmp_path / "smartread.db"
    client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")
    reloaded_client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    persisted_response = reloaded_client.get(f"/books/{book_id}/chapter-boundaries/1/quiz")

    assert response.status_code == 200
    assert [page["page_number"] for page in quiz_generator.calls[0]["pages"]] == [1, 2]
    assert quiz_generator.calls[0]["core_concepts"][0]["name"] == "Protected Attention"
    assert persisted_response.status_code == 200
    payload = persisted_response.json()
    assert payload["generation_status"] == "generated"
    assert payload["chapter"]["chapter_number"] == 1
    assert len(payload["quiz"]["questions"]) == 5
    assert payload["quiz"]["questions"][0] == {
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
    }
    assert payload["quiz"]["citations"][0] == {
        "id": "qc1",
        "source_location": f"book:{book_id}:page:1",
        "page_number": 1,
        "source_excerpt": (
            "Deep focus protects attention from constant switching so learners can "
            "practice deliberately."
        ),
    }


def test_resolve_persisted_quiz_citation_to_evidence_after_restart(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    database_path = tmp_path / "smartread.db"
    client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    reloaded_client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    response = reloaded_client.get(
        f"/books/{book_id}/chapter-boundaries/1/summary/citations/qc1/evidence"
    )

    assert response.status_code == 200
    assert response.json() == {
        "book_id": book_id,
        "chapter_number": 1,
        "citation_id": "qc1",
        "verification_status": "verified",
        "message": "Citation qc1 is verified.",
        "source_location": f"book:{book_id}:page:1",
        "page_number": 1,
        "source_excerpt": (
            "Deep focus protects attention from constant switching so learners can "
            "practice deliberately."
        ),
    }


def test_submit_correct_quiz_answer_returns_immediate_feedback(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    response = client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Constant switching"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "book_id": book_id,
        "chapter_number": 1,
        "question_id": "q1",
        "selected_answer": "Constant switching",
        "is_correct": True,
        "correct_answer": "Constant switching",
        "explanation": (
            "Protected attention reduces constant switching so deliberate practice is "
            "easier to repeat."
        ),
        "tested_concept": "Protected Attention",
        "citation_id": "qc1",
        "source_location": f"book:{book_id}:page:1",
        "page_number": 1,
        "source_excerpt": (
            "Deep focus protects attention from constant switching so learners can "
            "practice deliberately."
        ),
        "progress": {
            "answered_count": 1,
            "correct_count": 1,
            "incorrect_count": 0,
            "total_questions": 5,
        },
    }


def test_submit_incorrect_quiz_answer_shows_correct_answer_and_evidence(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    response = client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Long-term memory"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_correct"] is False
    assert payload["selected_answer"] == "Long-term memory"
    assert payload["correct_answer"] == "Constant switching"
    assert payload["explanation"] == (
        "Protected attention reduces constant switching so deliberate practice is "
        "easier to repeat."
    )
    assert payload["tested_concept"] == "Protected Attention"
    assert payload["citation_id"] == "qc1"
    assert payload["source_excerpt"] == (
        "Deep focus protects attention from constant switching so learners can "
        "practice deliberately."
    )
    assert payload["progress"] == {
        "answered_count": 1,
        "correct_count": 0,
        "incorrect_count": 1,
        "total_questions": 5,
    }


def test_incorrect_quiz_answer_creates_missed_concept(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    answer_response = client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Long-term memory"},
    )
    response = client.get(f"/books/{book_id}/chapter-boundaries/1/missed-concepts")

    assert answer_response.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {"missed_concept_count": 1}
    assert payload["missed_concepts"] == [
        {
            "book_id": book_id,
            "chapter_number": 1,
            "concept_name": "Protected Attention",
            "question_id": "q1",
            "quiz_answer_id": 1,
            "explanation": (
                "Protected attention reduces constant switching so deliberate practice is "
                "easier to repeat."
            ),
            "citation_id": "qc1",
            "source_location": f"book:{book_id}:page:1",
            "page_number": 1,
            "source_excerpt": (
                "Deep focus protects attention from constant switching so learners can "
                "practice deliberately."
            ),
        }
    ]


def test_correct_quiz_answer_does_not_create_missed_concept(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Constant switching"},
    )
    response = client.get(f"/books/{book_id}/chapter-boundaries/1/missed-concepts")

    assert response.status_code == 200
    assert response.json() == {
        "book_id": book_id,
        "chapter_number": 1,
        "summary": {"missed_concept_count": 0},
        "missed_concepts": [],
    }


def test_duplicate_missed_concepts_for_same_core_concept_are_avoided(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Long-term memory"},
    )
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q3",
        json={"selected_answer": "Retrieval Cues"},
    )
    response = client.get(f"/books/{book_id}/chapter-boundaries/1/missed-concepts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {"missed_concept_count": 1}
    assert [concept["concept_name"] for concept in payload["missed_concepts"]] == [
        "Protected Attention"
    ]


def test_missed_concepts_reload_after_restart(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    database_path = tmp_path / "smartread.db"
    client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Long-term memory"},
    )

    reloaded_client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    response = reloaded_client.get(f"/books/{book_id}/chapter-boundaries/1/missed-concepts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {"missed_concept_count": 1}
    assert payload["missed_concepts"][0]["concept_name"] == "Protected Attention"
    assert payload["missed_concepts"][0]["question_id"] == "q1"


def test_correct_retry_resolves_missed_concept_and_recalculates_mastery(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Long-term memory"},
    )

    retry_response = client.post(
        f"/books/{book_id}/chapter-boundaries/1/missed-concepts/q1/retry",
        json={"selected_answer": "Constant switching"},
    )
    progress_response = client.get(f"/books/{book_id}/chapter-boundaries/1/quiz/progress")
    missed_response = client.get(f"/books/{book_id}/chapter-boundaries/1/missed-concepts")

    assert retry_response.status_code == 200
    retry_payload = retry_response.json()
    assert retry_payload["selected_answer"] == "Constant switching"
    assert retry_payload["is_correct"] is True
    assert retry_payload["missed_concept_status"] == "resolved"
    assert retry_payload["progress"] == {
        "answered_count": 1,
        "correct_count": 1,
        "incorrect_count": 0,
        "total_questions": 5,
    }
    assert progress_response.json()["answers"][0]["selected_answer"] == "Constant switching"
    assert progress_response.json()["answers"][0]["is_correct"] is True
    assert missed_response.json()["missed_concepts"] == []


def test_incorrect_retry_keeps_missed_concept_active(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Long-term memory"},
    )

    retry_response = client.post(
        f"/books/{book_id}/chapter-boundaries/1/missed-concepts/q1/retry",
        json={"selected_answer": "Chapter boundaries"},
    )
    missed_response = client.get(f"/books/{book_id}/chapter-boundaries/1/missed-concepts")

    assert retry_response.status_code == 200
    retry_payload = retry_response.json()
    assert retry_payload["selected_answer"] == "Chapter boundaries"
    assert retry_payload["is_correct"] is False
    assert retry_payload["missed_concept_status"] == "active"
    assert retry_payload["progress"] == {
        "answered_count": 1,
        "correct_count": 0,
        "incorrect_count": 1,
        "total_questions": 5,
    }
    assert missed_response.json()["summary"] == {"missed_concept_count": 1}
    assert missed_response.json()["missed_concepts"][0]["question_id"] == "q1"


def test_duplicate_missed_question_retry_updates_one_saved_answer_record(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Long-term memory"},
    )

    client.post(
        f"/books/{book_id}/chapter-boundaries/1/missed-concepts/q1/retry",
        json={"selected_answer": "Chapter boundaries"},
    )
    retry_response = client.post(
        f"/books/{book_id}/chapter-boundaries/1/missed-concepts/q1/retry",
        json={"selected_answer": "Chapter boundaries"},
    )
    progress_response = client.get(f"/books/{book_id}/chapter-boundaries/1/quiz/progress")
    missed_response = client.get(f"/books/{book_id}/chapter-boundaries/1/missed-concepts")

    assert retry_response.status_code == 200
    assert len(progress_response.json()["answers"]) == 1
    assert progress_response.json()["answers"][0]["selected_answer"] == "Chapter boundaries"
    assert len(missed_response.json()["missed_concepts"]) == 1


def test_retry_rejects_question_that_is_not_currently_missed(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Constant switching"},
    )

    response = client.post(
        f"/books/{book_id}/chapter-boundaries/1/missed-concepts/q1/retry",
        json={"selected_answer": "Constant switching"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Missed question was not found."


def test_retry_results_reload_after_restart(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    database_path = tmp_path / "smartread.db"
    client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Long-term memory"},
    )
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/missed-concepts/q1/retry",
        json={"selected_answer": "Constant switching"},
    )

    reloaded_client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    progress_response = reloaded_client.get(
        f"/books/{book_id}/chapter-boundaries/1/quiz/progress"
    )
    missed_response = reloaded_client.get(
        f"/books/{book_id}/chapter-boundaries/1/missed-concepts"
    )

    assert progress_response.status_code == 200
    assert progress_response.json()["progress"] == {
        "answered_count": 1,
        "correct_count": 1,
        "incorrect_count": 0,
        "total_questions": 5,
    }
    assert progress_response.json()["answers"][0]["selected_answer"] == "Constant switching"
    assert missed_response.json()["missed_concepts"] == []


def test_list_missed_concepts_rejects_invalid_chapter_record(tmp_path):
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=FakeQuizGenerator(_valid_quiz_output()),
        )
    )

    response = client.get("/books/999/chapter-boundaries/1/missed-concepts")

    assert response.status_code == 404
    assert response.json()["detail"] == "Accepted chapter boundary was not found."


def test_quiz_progress_reloads_after_restart_without_duplicate_answer_records(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    database_path = tmp_path / "smartread.db"
    client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Long-term memory"},
    )
    client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/q1",
        json={"selected_answer": "Long-term memory"},
    )

    reloaded_client = TestClient(
        create_app(
            database_path=database_path,
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    response = reloaded_client.get(
        f"/books/{book_id}/chapter-boundaries/1/quiz/progress"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["progress"] == {
        "answered_count": 1,
        "correct_count": 0,
        "incorrect_count": 1,
        "total_questions": 5,
    }
    assert len(payload["answers"]) == 1
    assert payload["answers"][0]["question_id"] == "q1"
    assert payload["answers"][0]["selected_answer"] == "Long-term memory"
    assert payload["answers"][0]["is_correct"] is False
    assert payload["answers"][0]["correct_answer"] == "Constant switching"


def test_submit_quiz_answer_rejects_invalid_question_id(tmp_path):
    quiz_generator = FakeQuizGenerator(_valid_quiz_output())
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    response = client.post(
        f"/books/{book_id}/chapter-boundaries/1/quiz/answers/not-a-question",
        json={"selected_answer": "Constant switching"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Quiz question was not found."


def test_malformed_quiz_output_is_rejected_as_retryable_failure(tmp_path):
    output = _valid_quiz_output()
    output["questions"][0].pop("correct_answer")  # type: ignore[index]
    quiz_generator = FakeQuizGenerator(output)
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["retryable"] is True
    assert detail["message"] == "Quiz output must match the structured schema."
    assert detail["quiz"]["generation_status"] == "failed"
    assert detail["quiz"]["quiz"] is None


def test_quiz_citations_outside_accepted_chapter_are_rejected(tmp_path):
    output = _valid_quiz_output()
    output["citations"][0]["source_location"] = "book:1:page:3"  # type: ignore[index]
    output["citations"][0]["page_number"] = 3  # type: ignore[index]
    output["citations"][0]["source_excerpt"] = "Simple systems make review easier."  # type: ignore[index]
    quiz_generator = FakeQuizGenerator(output)
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    assert response.status_code == 422
    assert (
        response.json()["detail"]["message"]
        == "Quiz citations must point to stored pages inside the accepted chapter."
    )


def test_duplicate_quiz_questions_are_rejected(tmp_path):
    output = _valid_quiz_output()
    output["questions"][1]["question_text"] = output["questions"][0]["question_text"]  # type: ignore[index]
    quiz_generator = FakeQuizGenerator(output)
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Quiz questions must not be duplicated."


def test_ambiguous_quiz_answers_are_rejected(tmp_path):
    output = _valid_quiz_output()
    output["questions"][0]["answer_options"] = [  # type: ignore[index]
        "It depends",
        "Constant switching",
        "Long-term memory",
    ]
    output["questions"][0]["correct_answer"] = "It depends"  # type: ignore[index]
    quiz_generator = FakeQuizGenerator(output)
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Quiz questions need one clear correct answer."


def test_unsupported_quiz_questions_are_rejected(tmp_path):
    output = _valid_quiz_output()
    output["questions"][0]["question_text"] = (  # type: ignore[index]
        "What schedules memory reviews across increasing intervals?"
    )
    output["questions"][0]["answer_options"] = [  # type: ignore[index]
        "Spaced repetition",
        "Protected attention",
        "Source citations",
    ]
    output["questions"][0]["correct_answer"] = "Spaced repetition"  # type: ignore[index]
    output["questions"][0]["explanation"] = (  # type: ignore[index]
        "Spaced repetition schedules reviews across increasing intervals."
    )
    quiz_generator = FakeQuizGenerator(output)
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Source excerpts must support quiz questions."


def test_trivia_only_quiz_questions_are_rejected(tmp_path):
    output = _valid_quiz_output()
    output["questions"][0]["question_text"] = (  # type: ignore[index]
        "On what page does protected attention appear?"
    )
    quiz_generator = FakeQuizGenerator(output)
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
            quiz_generator=quiz_generator,
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Quiz questions must test understanding, not trivia."


def test_openai_quiz_generation_requires_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SMARTREAD_OPENAI_MODEL", raising=False)
    client = TestClient(
        create_app(
            database_path=tmp_path / "smartread.db",
            concepts_generator=FakeConceptsTakeawaysGenerator(),
        )
    )
    book_id = _upload_extract_accept_and_generate_concepts(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/quiz")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "OpenAI generation is not configured. Set OPENAI_API_KEY and retry."
    assert detail["retryable"] is True
    assert detail["quiz"]["provider"] == "openai"
    assert detail["quiz"]["model"] == "gpt-5.5"


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
                "explanation": "Retrieval cues help learners recall ideas and connect practice.",
                "why_it_matters": "They matter because recall supports long term memory.",
                "example": None,
                "citation_ids": ["c2"],
            },
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
                "question_text": "True or false: retrieval cues help learners recall ideas later.",
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
                "question_text": (
                    "What makes deliberate practice easier to repeat in this chapter?"
                ),
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


def _upload_extract_accept_and_generate_concepts(client: TestClient) -> int:
    pdf_bytes = build_pdf_with_text_pages(
        [
            (
                "Chapter 1: Focus\n"
                "Deep focus protects attention from constant switching so learners can "
                "practice deliberately."
            ),
            (
                "Retrieval cues help learners recall ideas later and connect practice to "
                "long term memory. A protected block reduces context switching and makes "
                "deliberate practice easier to repeat."
            ),
            "Chapter 2: Systems\nSimple systems make review easier.",
        ]
    )
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("quiz.pdf", pdf_bytes, "application/pdf")},
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
    client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")
    return book_id
