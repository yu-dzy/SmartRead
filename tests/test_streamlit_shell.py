from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_shell_renders_design_a_placeholders_when_api_is_unavailable(
    monkeypatch,
):
    monkeypatch.setenv("SMARTREAD_API_URL", "http://127.0.0.1:9")

    app_path = Path(__file__).parents[1] / "smartread_frontend" / "app.py"
    app = AppTest.from_file(str(app_path))
    app.run(timeout=5)

    page_text = "\n".join(element.value for element in app.markdown)

    assert not app.exception
    assert "SmartRead" in page_text
    assert "FastAPI unavailable" in page_text
    assert "Book Map" in page_text
    assert "Chapter Lesson" in page_text
    assert "Evidence" in page_text
    assert "Mastery" in page_text
