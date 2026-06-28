from fastapi.testclient import TestClient

from smartread_api.main import create_app
from tests.pdf_fixtures import build_pdf_with_text_pages


class FakeSummaryGenerator:
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.calls: list[dict[str, object]] = []

    def generate_summary(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
    ) -> dict[str, object]:
        self.calls.append({"chapter": chapter, "pages": pages})
        return self.output


def test_generate_cited_summary_for_one_accepted_chapter_and_persist_it(tmp_path):
    generator = FakeSummaryGenerator(
        {
            "central_argument": {
                "claim": "Focus improves when attention is protected from constant switching.",
                "citation_ids": ["c1"],
            },
            "supporting_ideas": [
                {
                    "claim": "The chapter argues that protected attention makes deep work possible.",
                    "citation_ids": ["c2"],
                }
            ],
            "citations": [
                {
                    "id": "c1",
                    "source_location": "book:1:page:1",
                    "page_number": 1,
                    "source_excerpt": "Focus improves when attention is protected from constant switching.",
                },
                {
                    "id": "c2",
                    "source_location": "book:1:page:2",
                    "page_number": 2,
                    "source_excerpt": "Protected attention makes deep work possible for learners.",
                },
            ],
        }
    )
    database_path = tmp_path / "smartread.db"
    client = TestClient(create_app(database_path=database_path, summary_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/summary")
    reloaded_client = TestClient(create_app(database_path=database_path, summary_generator=generator))
    persisted_response = reloaded_client.get(f"/books/{book_id}/chapter-boundaries/1/summary")

    assert response.status_code == 200
    assert [
        page["page_number"] for page in generator.calls[0]["pages"]  # type: ignore[index]
    ] == [1, 2]
    assert persisted_response.status_code == 200
    payload = persisted_response.json()
    assert payload["generation_status"] == "generated"
    assert payload["chapter"]["chapter_number"] == 1
    assert payload["summary"]["central_argument"]["claim"].startswith("Focus improves")
    assert payload["summary"]["citations"] == [
        {
            "id": "c1",
            "source_location": f"book:{book_id}:page:1",
            "page_number": 1,
            "source_excerpt": "Focus improves when attention is protected from constant switching.",
        },
        {
            "id": "c2",
            "source_location": f"book:{book_id}:page:2",
            "page_number": 2,
            "source_excerpt": "Protected attention makes deep work possible for learners.",
        },
    ]


def test_schema_validation_rejects_extra_summary_fields_as_retryable_failure(tmp_path):
    generator = FakeSummaryGenerator(
        {
            "central_argument": {
                "claim": "Focus improves when attention is protected from constant switching.",
                "citation_ids": ["c1"],
            },
            "supporting_ideas": [
                {
                    "claim": "Protected attention makes deep work possible.",
                    "citation_ids": ["c1"],
                }
            ],
            "citations": [
                {
                    "id": "c1",
                    "source_location": "book:1:page:1",
                    "page_number": 1,
                    "source_excerpt": "Focus improves when attention is protected from constant switching.",
                }
            ],
            "key_takeaways": ["This belongs to Issue #8, not the Summary slice."],
        }
    )
    client = TestClient(create_app(database_path=tmp_path / "smartread.db", summary_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/summary")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["retryable"] is True
    assert detail["message"] == "Summary output contains unsupported fields."
    assert detail["summary"]["generation_status"] == "failed"


def test_citation_outside_accepted_chapter_is_rejected(tmp_path):
    generator = FakeSummaryGenerator(
        {
            "central_argument": {
                "claim": "Recall improves through active practice.",
                "citation_ids": ["c1"],
            },
            "supporting_ideas": [
                {
                    "claim": "Active practice strengthens recall.",
                    "citation_ids": ["c1"],
                }
            ],
            "citations": [
                {
                    "id": "c1",
                    "source_location": "book:1:page:3",
                    "page_number": 3,
                    "source_excerpt": "Recall improves through active practice.",
                }
            ],
        }
    )
    client = TestClient(create_app(database_path=tmp_path / "smartread.db", summary_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/summary")

    assert response.status_code == 422
    assert (
        response.json()["detail"]["message"]
        == "Citations must point to stored pages inside the accepted chapter."
    )


def test_unsupported_claim_source_excerpt_is_rejected(tmp_path):
    generator = FakeSummaryGenerator(
        {
            "central_argument": {
                "claim": "Spaced repetition is the chapter's main argument.",
                "citation_ids": ["c1"],
            },
            "supporting_ideas": [
                {
                    "claim": "Spaced repetition should drive the study plan.",
                    "citation_ids": ["c1"],
                }
            ],
            "citations": [
                {
                    "id": "c1",
                    "source_location": "book:1:page:1",
                    "page_number": 1,
                    "source_excerpt": "Focus improves when attention is protected from constant switching.",
                }
            ],
        }
    )
    client = TestClient(create_app(database_path=tmp_path / "smartread.db", summary_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/summary")

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Source excerpts must support cited claims."


def test_retrying_summary_generation_updates_one_persisted_summary(tmp_path):
    first_output = {
        "central_argument": {
            "claim": "Focus improves when attention is protected from constant switching.",
            "citation_ids": ["c1"],
        },
        "supporting_ideas": [
            {
                "claim": "Protected attention makes deep work possible.",
                "citation_ids": ["c1"],
            }
        ],
        "citations": [
            {
                "id": "c1",
                "source_location": "book:1:page:1",
                "page_number": 1,
                "source_excerpt": "Focus improves when attention is protected from constant switching.",
            }
        ],
    }
    second_output = {
        "central_argument": {
            "claim": "Protected attention makes deep work possible for learners.",
            "citation_ids": ["c1"],
        },
        "supporting_ideas": [
            {
                "claim": "Focus improves when attention is protected.",
                "citation_ids": ["c1"],
            }
        ],
        "citations": [
            {
                "id": "c1",
                "source_location": "book:1:page:2",
                "page_number": 2,
                "source_excerpt": "Protected attention makes deep work possible for learners.",
            }
        ],
    }
    generator = CyclingSummaryGenerator([first_output, second_output])
    client = TestClient(create_app(database_path=tmp_path / "smartread.db", summary_generator=generator))
    book_id = _upload_extract_and_accept_chapter(client)

    first_response = client.post(f"/books/{book_id}/chapter-boundaries/1/summary")
    retry_response = client.post(f"/books/{book_id}/chapter-boundaries/1/summary")
    persisted_response = client.get(f"/books/{book_id}/chapter-boundaries/1/summary")

    assert first_response.status_code == 200
    assert retry_response.status_code == 200
    assert persisted_response.json()["summary"] == retry_response.json()["summary"]
    assert persisted_response.json()["summary"]["central_argument"]["claim"].startswith(
        "Protected attention"
    )


def test_openai_generation_requires_api_key_and_uses_defined_default_model(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SMARTREAD_OPENAI_MODEL", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "smartread.db"))
    book_id = _upload_extract_and_accept_chapter(client)

    response = client.post(f"/books/{book_id}/chapter-boundaries/1/summary")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "OpenAI generation is not configured. Set OPENAI_API_KEY and retry."
    assert detail["retryable"] is True
    assert detail["summary"]["provider"] == "openai"
    assert detail["summary"]["model"] == "gpt-5.5"


class CyclingSummaryGenerator:
    provider = "test"
    model = "fake"

    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self.outputs = outputs

    def generate_summary(
        self,
        *,
        chapter: dict[str, object],
        pages: list[dict[str, object]],
    ) -> dict[str, object]:
        return self.outputs.pop(0)


def _upload_extract_and_accept_chapter(client: TestClient) -> int:
    pdf_bytes = build_pdf_with_text_pages(
        [
            "Chapter 1: Focus\nFocus improves when attention is protected from constant switching.",
            "Protected attention makes deep work possible for learners.",
            "Chapter 2: Recall\nRecall improves through active practice.",
        ]
    )
    upload_response = client.post(
        "/books/uploads",
        files={"file": ("summary.pdf", pdf_bytes, "application/pdf")},
    )
    book_id = upload_response.json()["id"]
    client.post(f"/books/{book_id}/extraction")
    client.post(f"/books/{book_id}/chapter-detection")
    client.put(
        f"/books/{book_id}/chapter-boundaries",
        json={
            "chapters": [
                {"chapter_number": 1, "title": "Focus", "start_page": 1, "end_page": 2},
                {"chapter_number": 2, "title": "Recall", "start_page": 3, "end_page": 3},
            ]
        },
    )
    return book_id
