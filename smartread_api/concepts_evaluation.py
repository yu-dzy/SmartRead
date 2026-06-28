from __future__ import annotations

from typing import Any

from smartread_api.summary_evaluation import build_summary_evaluation_cases


def build_concepts_takeaways_evaluation_cases() -> list[dict[str, Any]]:
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
                    "Generate cited SmartRead Core Concepts and Key Takeaways. Each Core "
                    "Concept must include a name, clear explanation, why it matters, optional "
                    "example, citation ids, source locations, page numbers, and short source "
                    "excerpts that support the claim. Key Takeaways must be concise, "
                    "chapter-specific, grounded, and cited."
                ),
                "generic_baseline_prompt": f"Summarize this chapter.\n\n{chapter_text}",
                "comparison_criteria": [
                    "concept_specificity",
                    "takeaway_grounding",
                    "source_support",
                    "citation_accuracy",
                    "duplicate_concept_rejection",
                    "schema_validity",
                ],
            }
        )

    return cases
