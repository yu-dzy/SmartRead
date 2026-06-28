from fastapi.testclient import TestClient

from smartread_api.main import create_app
from tests.pdf_fixtures import build_pdf_with_text_pages


class FakeConceptsTakeawaysGenerator:
    provider = "test"
    model = "fake"

    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.calls: list[dict[str, object]] = []

    def generate_concepts_takeaways(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
    ) -> dict[str, object]:
        self.calls.append({"chapter": chapter, "pages": pages})
        return self.output


def test_generate_core_concepts_and_key_takeaways_for_one_accepted_chapter(tmp_path):
    generator = FakeConceptsTakeawaysGenerator(_valid_concepts_takeaways_output())
    database_path = tmp_path / "smartread.db"
    client = TestClient(create_app(database_path=database_path, concepts_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")
    reloaded_client = TestClient(
        create_app(database_path=database_path, concepts_generator=generator)
    )
    persisted_response = reloaded_client.get(
        f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways"
    )

    assert response.status_code == 200
    assert [page["page_number"] for page in generator.calls[0]["pages"]] == [1, 2]
    assert persisted_response.status_code == 200
    payload = persisted_response.json()
    assert payload["generation_status"] == "generated"
    assert payload["chapter"]["chapter_number"] == 1
    assert payload["content"]["core_concepts"] == [
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
        }
    ]
    assert payload["content"]["key_takeaways"] == [
        {
            "text": "Protecting attention makes deliberate practice easier.",
            "citation_ids": ["c1"],
        },
        {
            "text": "Retrieval cues help learners recall and connect ideas later.",
            "citation_ids": ["c2"],
        },
    ]
    assert payload["content"]["citations"] == [
        {
            "id": "c1",
            "source_location": f"book:{book_id}:page:1",
            "page_number": 1,
            "source_excerpt": (
                "Deep focus protects attention from constant switching so learners can "
                "practice deliberately."
            ),
        },
        {
            "id": "c2",
            "source_location": f"book:{book_id}:page:2",
            "page_number": 2,
            "source_excerpt": (
                "Retrieval cues help learners recall ideas later and connect practice to "
                "long term memory."
            ),
        },
    ]


def test_resolve_persisted_core_concept_citation_to_evidence_after_restart(tmp_path):
    generator = FakeConceptsTakeawaysGenerator(_valid_concepts_takeaways_output())
    database_path = tmp_path / "smartread.db"
    client = TestClient(create_app(database_path=database_path, concepts_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)
    client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")

    reloaded_client = TestClient(
        create_app(database_path=database_path, concepts_generator=generator)
    )
    response = reloaded_client.get(
        f"/books/{book_id}/chapter-boundaries/1/summary/citations/c1/evidence"
    )

    assert response.status_code == 200
    assert response.json() == {
        "book_id": book_id,
        "chapter_number": 1,
        "citation_id": "c1",
        "verification_status": "verified",
        "message": "Citation c1 is verified.",
        "source_location": f"book:{book_id}:page:1",
        "page_number": 1,
        "source_excerpt": (
            "Deep focus protects attention from constant switching so learners can "
            "practice deliberately."
        ),
    }


def test_malformed_concepts_takeaways_output_is_rejected_as_retryable_failure(tmp_path):
    malformed_output = _valid_concepts_takeaways_output()
    malformed_output["core_concepts"] = [
        {
            "name": "Protected Attention",
            "explanation": "Protected attention reduces constant switching.",
            "citation_ids": ["c1"],
        }
    ]
    generator = FakeConceptsTakeawaysGenerator(malformed_output)
    client = TestClient(create_app(database_path=tmp_path / "smartread.db", concepts_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["retryable"] is True
    assert detail["message"] == "Concept and takeaway output must match the structured schema."
    assert detail["concepts_takeaways"]["generation_status"] == "failed"
    assert detail["concepts_takeaways"]["content"] is None


def test_concepts_takeaways_citations_outside_accepted_chapter_are_rejected(tmp_path):
    output = _valid_concepts_takeaways_output()
    output["citations"] = [
        {
            "id": "c1",
            "source_location": "book:1:page:3",
            "page_number": 3,
            "source_excerpt": "Simple systems make review easier.",
        }
    ]
    output["core_concepts"][0]["citation_ids"] = ["c1"]  # type: ignore[index]
    output["key_takeaways"] = [
        {"text": "Simple systems make review easier.", "citation_ids": ["c1"]}
    ]
    generator = FakeConceptsTakeawaysGenerator(output)
    client = TestClient(create_app(database_path=tmp_path / "smartread.db", concepts_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")

    assert response.status_code == 422
    assert (
        response.json()["detail"]["message"]
        == "Citations must point to stored pages inside the accepted chapter."
    )


def test_generic_core_concepts_are_rejected(tmp_path):
    output = _valid_concepts_takeaways_output()
    output["core_concepts"][0]["name"] = "Productivity"  # type: ignore[index]
    generator = FakeConceptsTakeawaysGenerator(output)
    client = TestClient(create_app(database_path=tmp_path / "smartread.db", concepts_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Core Concepts must be specific, not generic."


def test_duplicate_core_concepts_are_rejected(tmp_path):
    output = _valid_concepts_takeaways_output()
    output["core_concepts"].append(  # type: ignore[union-attr]
        {
            "name": "Protected Attention",
            "explanation": "Protected attention keeps deliberate practice on track.",
            "why_it_matters": "It matters because attention supports deliberate practice.",
            "example": None,
            "citation_ids": ["c1"],
        }
    )
    generator = FakeConceptsTakeawaysGenerator(output)
    client = TestClient(create_app(database_path=tmp_path / "smartread.db", concepts_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Core Concepts must not be duplicated."


def test_unsupported_concept_or_takeaway_claims_are_rejected(tmp_path):
    output = _valid_concepts_takeaways_output()
    output["core_concepts"][0]["name"] = "Spaced Repetition"  # type: ignore[index]
    output["core_concepts"][0]["explanation"] = (  # type: ignore[index]
        "Spaced repetition schedules reviews across increasing intervals."
    )
    output["core_concepts"][0]["why_it_matters"] = (  # type: ignore[index]
        "It matters because interval scheduling strengthens memory."
    )
    generator = FakeConceptsTakeawaysGenerator(output)
    client = TestClient(create_app(database_path=tmp_path / "smartread.db", concepts_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")

    assert response.status_code == 422
    assert (
        response.json()["detail"]["message"]
        == "Source excerpts must support concept and takeaway claims."
    )


def test_empty_core_concepts_are_rejected(tmp_path):
    output = _valid_concepts_takeaways_output()
    output["core_concepts"] = []
    generator = FakeConceptsTakeawaysGenerator(output)
    client = TestClient(create_app(database_path=tmp_path / "smartread.db", concepts_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == (
        "Concept and takeaway output must match the structured schema."
    )


def test_openai_concepts_takeaways_generation_requires_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SMARTREAD_OPENAI_MODEL", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/concepts-takeaways")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "OpenAI generation is not configured. Set OPENAI_API_KEY and retry."
    assert detail["retryable"] is True
    assert detail["concepts_takeaways"]["provider"] == "openai"
    assert detail["concepts_takeaways"]["model"] == "gpt-5.5"


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


def _upload_extract_and_accept_chapter(client: TestClient) -> int:
    pdf_bytes = build_pdf_with_text_pages(
        [
            (
                "Chapter 1: Focus\n"
                "Deep focus protects attention from constant switching so learners can "
                "practice deliberately."
            ),
            (
                "Retrieval cues help learners recall ideas later and connect practice to "
                "long term memory."
            ),
            "Chapter 2: Systems\nSimple systems make review easier.",
        ]
    )
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("concepts.pdf", pdf_bytes, "application/pdf")},
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
