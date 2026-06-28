import os

import streamlit as st

try:
    from smartread_frontend.health import get_api_status
    from smartread_frontend.uploads import (
        detect_chapters_from_api,
        extract_pdf_text_from_api,
        get_uploaded_books,
        upload_pdf_to_api,
    )
except ModuleNotFoundError as error:
    if error.name != "smartread_frontend":
        raise

    from health import get_api_status
    from uploads import (
        detect_chapters_from_api,
        extract_pdf_text_from_api,
        get_uploaded_books,
        upload_pdf_to_api,
    )


PRIVATE_UPLOAD_NOTICE = (
    "Only upload books you own or have permission to use. "
    "SmartRead keeps this upload private for your personal learning workflow."
)


def main() -> None:
    st.set_page_config(page_title="SmartRead", page_icon="SR", layout="wide")

    api_url = os.environ.get("SMARTREAD_API_URL", "http://127.0.0.1:8000")
    status = get_api_status(api_url)
    books_result = get_uploaded_books(api_url) if status.connected else None

    st.markdown("# SmartRead")
    st.markdown("A private learning system for cited chapter lessons and active recall.")
    st.markdown(f"**{status.heading}**")
    st.markdown(status.detail)

    left, center, right = st.columns([1, 2, 1], gap="large")

    with left:
        st.markdown("## Book Map")
        st.markdown(PRIVATE_UPLOAD_NOTICE)
        uploaded_file = st.file_uploader(
            "Upload a user-owned PDF",
            type=["pdf"],
            accept_multiple_files=False,
        )
        if st.button("Upload PDF"):
            if uploaded_file is None:
                st.warning("Choose a PDF before uploading.")
            else:
                with st.spinner("Uploading PDF..."):
                    upload_result = upload_pdf_to_api(
                        api_url,
                        filename=uploaded_file.name,
                        content=uploaded_file.getvalue(),
                        content_type=uploaded_file.type or "application/pdf",
                    )
                if upload_result.success:
                    st.success(upload_result.message)
                    st.markdown(upload_result.message)
                else:
                    st.error(upload_result.message)
                    st.markdown(upload_result.message)
                    if upload_result.retryable:
                        st.markdown("You can retry with the same file or choose a replacement PDF.")
                books_result = get_uploaded_books(api_url)

        st.markdown("### Uploaded Books")
        if books_result is None:
            st.markdown("Start FastAPI to load uploaded books.")
        elif not books_result.success:
            st.error(books_result.message)
        elif not books_result.books:
            st.markdown("No uploaded books yet.")
        else:
            for book in books_result.books:
                st.markdown(
                    f"- **{book['original_filename']}** - "
                    f"{book['upload_status']} - "
                    f"{book['processing_status']} - "
                    f"{book['file_size']} bytes"
                )
                if st.button("Extract text", key=f"extract_{book['id']}"):
                    with st.spinner("Extracting page text..."):
                        extraction_result = extract_pdf_text_from_api(
                            api_url,
                            book_id=book["id"],
                        )
                    if extraction_result.success:
                        st.success(extraction_result.message)
                        st.markdown(extraction_result.message)
                        if extraction_result.book is not None:
                            st.markdown(
                                f"Extraction status: {extraction_result.book['processing_status']}"
                            )
                    else:
                        st.error(extraction_result.message)
                        st.markdown(extraction_result.message)
                        if extraction_result.retryable:
                            st.markdown("Retry extraction or upload a cleaner PDF.")
                    books_result = get_uploaded_books(api_url)
                if book.get("processing_status") == "extracted":
                    if st.button("Detect chapters", key=f"detect_{book['id']}"):
                        with st.spinner("Detecting chapters..."):
                            detection_result = detect_chapters_from_api(
                                api_url,
                                book_id=book["id"],
                            )
                        if detection_result.success:
                            st.success(detection_result.message)
                            st.markdown(detection_result.message)
                            warning = detection_result.summary.get("warning")
                            if warning:
                                st.warning(warning)
                                st.markdown(warning)
                            _render_book_map(detection_result.chapters)
                        else:
                            st.error(detection_result.message)
                            st.markdown(detection_result.message)
                            if detection_result.retryable:
                                st.markdown("Retry chapter detection after text extraction.")
                        books_result = get_uploaded_books(api_url)

    with center:
        st.markdown("## Chapter Lesson")
        st.markdown("Summary, Core Concepts, Key Takeaways, Quiz, and Review will live here.")

    with right:
        st.markdown("## Evidence")
        st.markdown("Clicked source excerpts will appear here.")
        st.markdown("## Mastery")
        st.markdown("Quiz progress and missed concepts will appear here.")


def _render_book_map(chapters: list[dict[str, object]]) -> None:
    st.markdown("### Detected Chapters")
    if not chapters:
        st.markdown("No chapters could be detected.")
        st.markdown("Manual chapter review will be required before lessons.")
    else:
        for chapter in chapters:
            st.markdown(
                f"- **{chapter['chapter_number']}. {chapter['title']}** - "
                f"Pages {chapter['start_page']}-{chapter['end_page']} - "
                f"{chapter['confidence']} confidence"
            )
    st.markdown("Chapter lesson generation remains unavailable until boundaries are reviewed.")


if __name__ == "__main__":
    main()
