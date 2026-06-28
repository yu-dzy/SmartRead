from __future__ import annotations

from typing import Any

from smartread_api.summary_evaluation import build_summary_evaluation_cases


def build_quiz_evaluation_cases() -> list[dict[str, Any]]:
    cases = []
    for summary_case in build_summary_evaluation_cases():
        source_pages = summary_case["source_pages"]
        chapter_text = "\n\n".join(str(page["extracted_text"]) for page in source_pages)
        cases.append(
            {
                "domain": summary_case["domain"],
                "title": summary_case["title"],
                "source_pages": source_pages,
                "smartread_prompt": (
                    "Generate exactly five cited SmartRead quiz questions for this chapter. "
                    "Each question must link to one Core Concept, use objective answer "
                    "options, include one clear correct answer, include an explanation, "
                    "avoid trivia, and include a citation with a source excerpt that "
                    "supports the question."
                ),
                "generic_baseline_prompt": (
                    f"Summarize this chapter and generate a quiz.\n\n{chapter_text}"
                ),
                "comparison_criteria": [
                    "core_concept_linkage",
                    "answer_clarity",
                    "source_support",
                    "citation_accuracy",
                    "trivia_avoidance",
                    "application_over_recall",
                    "schema_validity",
                ],
            }
        )

    return cases
