import os

import streamlit as st
try:
    from smartread_frontend.health import get_api_status
except ModuleNotFoundError as error:
    if error.name != "smartread_frontend":
        raise

    from health import get_api_status

def main() -> None:
    st.set_page_config(page_title="SmartRead", page_icon="SR", layout="wide")

    api_url = os.environ.get("SMARTREAD_API_URL", "http://127.0.0.1:8000")
    status = get_api_status(api_url)

    st.markdown("# SmartRead")
    st.markdown("A private learning system for cited chapter lessons and active recall.")
    st.markdown(f"**{status.heading}**")
    st.markdown(status.detail)

    left, center, right = st.columns([1, 2, 1], gap="large")

    with left:
        st.markdown("## Book Map")
        st.markdown("Upload and chapter progress will appear here in later issues.")

    with center:
        st.markdown("## Chapter Lesson")
        st.markdown("Summary, Core Concepts, Key Takeaways, Quiz, and Review will live here.")

    with right:
        st.markdown("## Evidence")
        st.markdown("Clicked source excerpts will appear here.")
        st.markdown("## Mastery")
        st.markdown("Quiz progress and missed concepts will appear here.")


if __name__ == "__main__":
    main()
