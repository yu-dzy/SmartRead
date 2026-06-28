from smartread_api.summary_evaluation import build_summary_evaluation_cases


def test_summary_evaluation_uses_three_fixtures_and_generic_summary_baseline():
    cases = build_summary_evaluation_cases()

    assert len(cases) == 3
    assert {case["domain"] for case in cases} == {
        "personal-development",
        "business",
        "practical-learning",
    }
    for case in cases:
        assert "summarize this chapter" in case["generic_baseline_prompt"].lower()
        assert "citation" in case["smartread_prompt"].lower()
        assert case["source_pages"]
        assert "source_support" in case["comparison_criteria"]
