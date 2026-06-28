from smartread_api.quiz_evaluation import build_quiz_evaluation_cases


def test_quiz_evaluation_uses_three_fixtures_and_generic_quiz_baseline():
    cases = build_quiz_evaluation_cases()

    assert len(cases) == 3
    assert {case["domain"] for case in cases} == {
        "personal-development",
        "business",
        "practical-learning",
    }
    for case in cases:
        smartread_prompt = case["smartread_prompt"].lower()
        assert "five" in smartread_prompt
        assert "quiz questions" in smartread_prompt
        assert "core concept" in smartread_prompt
        assert "citation" in smartread_prompt
        assert "generate a quiz" in case["generic_baseline_prompt"].lower()
        assert case["source_pages"]
        assert "source_support" in case["comparison_criteria"]
        assert "answer_clarity" in case["comparison_criteria"]
        assert "trivia_avoidance" in case["comparison_criteria"]
