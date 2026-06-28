from __future__ import annotations

from typing import Any


def build_summary_evaluation_cases() -> list[dict[str, Any]]:
    return [
        _build_case(
            domain="personal-development",
            title="Attention Blocks",
            source_pages=[
                {
                    "page_number": 1,
                    "source_location": "fixture:personal-development:page:1",
                    "extracted_text": (
                        "The chapter argues that personal change becomes easier when the "
                        "learner protects attention in small blocks instead of relying on willpower."
                    ),
                },
                {
                    "page_number": 2,
                    "source_location": "fixture:personal-development:page:2",
                    "extracted_text": (
                        "A protected block reduces context switching and makes deliberate "
                        "practice easier to repeat."
                    ),
                },
            ],
        ),
        _build_case(
            domain="business",
            title="Strategy Tradeoffs",
            source_pages=[
                {
                    "page_number": 1,
                    "source_location": "fixture:business:page:1",
                    "extracted_text": (
                        "The chapter's central argument is that strategy requires choosing "
                        "which customers and capabilities the company will not pursue."
                    ),
                },
                {
                    "page_number": 2,
                    "source_location": "fixture:business:page:2",
                    "extracted_text": (
                        "The author supports this with a warning that vague priorities "
                        "spread teams across incompatible goals."
                    ),
                },
            ],
        ),
        _build_case(
            domain="practical-learning",
            title="Retrieval Practice",
            source_pages=[
                {
                    "page_number": 1,
                    "source_location": "fixture:practical-learning:page:1",
                    "extracted_text": (
                        "The chapter explains that learners remember more when they retrieve "
                        "an idea before rereading the explanation."
                    ),
                },
                {
                    "page_number": 2,
                    "source_location": "fixture:practical-learning:page:2",
                    "extracted_text": (
                        "Short feedback after retrieval helps correct misunderstandings "
                        "while the memory trace is still active."
                    ),
                },
            ],
        ),
    ]


def _build_case(
    *,
    domain: str,
    title: str,
    source_pages: list[dict[str, object]],
) -> dict[str, Any]:
    chapter_text = "\n\n".join(str(page["extracted_text"]) for page in source_pages)
    return {
        "domain": domain,
        "title": title,
        "source_pages": source_pages,
        "smartread_prompt": (
            "Generate a cited SmartRead Summary with a central argument, important "
            "supporting ideas, citation ids, source locations, page numbers, and "
            "short source excerpts that support each claim."
        ),
        "generic_baseline_prompt": f"Summarize this chapter.\n\n{chapter_text}",
        "comparison_criteria": [
            "central_argument",
            "important_supporting_ideas",
            "source_support",
            "citation_accuracy",
            "specificity_over_generic_advice",
        ],
    }
