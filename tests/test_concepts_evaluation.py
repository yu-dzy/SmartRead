from smartread_api.concepts_evaluation import build_concepts_takeaways_evaluation_cases


def test_concepts_takeaways_evaluation_uses_three_fixtures_and_generic_summary_baseline():
    cases = build_concepts_takeaways_evaluation_cases()

    assert len(cases) == 3
    assert {case["domain"] for case in cases} == {
        "personal-development",
        "business",
        "practical-learning",
    }
    for case in cases:
        smartread_prompt = case["smartread_prompt"].lower()
        assert "core concepts" in smartread_prompt
        assert "key takeaways" in smartread_prompt
        assert "citation" in smartread_prompt
        assert "summarize this chapter" in case["generic_baseline_prompt"].lower()
        assert case["source_pages"]
        assert "source_support" in case["comparison_criteria"]
        assert "citation_accuracy" in case["comparison_criteria"]
        assert "concept_specificity" in case["comparison_criteria"]
