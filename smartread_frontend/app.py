import os

import streamlit as st

try:
    from smartread_frontend.health import get_api_status
    from smartread_frontend.uploads import (
        detect_chapters_from_api,
        extract_pdf_text_from_api,
        generate_chapter_summary_from_api,
        generate_concepts_takeaways_from_api,
        generate_quiz_from_api,
        get_chapter_boundaries_from_api,
        get_chapter_summary_from_api,
        get_citation_evidence_from_api,
        get_concepts_takeaways_from_api,
        get_quiz_from_api,
        get_uploaded_books,
        save_chapter_boundaries_to_api,
        upload_pdf_to_api,
    )
except ModuleNotFoundError as error:
    if error.name != "smartread_frontend":
        raise

    from health import get_api_status
    from uploads import (
        detect_chapters_from_api,
        extract_pdf_text_from_api,
        generate_chapter_summary_from_api,
        generate_concepts_takeaways_from_api,
        generate_quiz_from_api,
        get_chapter_boundaries_from_api,
        get_chapter_summary_from_api,
        get_citation_evidence_from_api,
        get_concepts_takeaways_from_api,
        get_quiz_from_api,
        get_uploaded_books,
        save_chapter_boundaries_to_api,
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
                    review_key = f"review_chapters_{book['id']}"
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
                            st.session_state[review_key] = detection_result.chapters
                        else:
                            st.error(detection_result.message)
                            st.markdown(detection_result.message)
                            if detection_result.retryable:
                                st.markdown("Retry chapter detection after text extraction.")
                        books_result = get_uploaded_books(api_url)
                    if review_key in st.session_state:
                        _render_book_map(st.session_state[review_key])
                        _render_chapter_boundary_review(
                            api_url=api_url,
                            book_id=book["id"],
                            chapters=st.session_state[review_key],
                            review_key=review_key,
                        )

    with center:
        st.markdown("## Chapter Lesson")
        summary_tab, concepts_tab, takeaways_tab, quiz_tab, review_tab = st.tabs(
            ["Summary", "Core Concepts", "Key Takeaways", "Quiz", "Review"]
        )
        with summary_tab:
            _render_summary_tab(api_url=api_url, books_result=books_result)
        with concepts_tab:
            _render_core_concepts_tab(api_url=api_url, books_result=books_result)
        with takeaways_tab:
            _render_key_takeaways_tab(api_url=api_url, books_result=books_result)
        with quiz_tab:
            _render_quiz_tab(api_url=api_url, books_result=books_result)
        with review_tab:
            st.markdown("Missed-concept review will be generated in a later MVP slice.")

    with right:
        st.markdown("## Evidence")
        _render_evidence_panel(api_url=api_url)
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


def _render_chapter_boundary_review(
    *,
    api_url: str,
    book_id: int,
    chapters: list[dict[str, object]],
    review_key: str,
) -> None:
    st.markdown("### Review Boundaries")
    edited_chapters = []
    for index, chapter in enumerate(chapters, start=1):
        chapter_number = int(chapter.get("chapter_number", index))
        title = st.text_input(
            f"Chapter {chapter_number} title",
            value=str(chapter["title"]),
            key=f"title_{book_id}_{chapter_number}",
        )
        start_page = st.number_input(
            f"Chapter {chapter_number} start page",
            min_value=1,
            value=int(chapter["start_page"]),
            step=1,
            key=f"start_{book_id}_{chapter_number}",
        )
        end_page = st.number_input(
            f"Chapter {chapter_number} end page",
            min_value=1,
            value=int(chapter["end_page"]),
            step=1,
            key=f"end_{book_id}_{chapter_number}",
        )
        edited_chapters.append(
            {
                "chapter_number": chapter_number,
                "title": title,
                "start_page": int(start_page),
                "end_page": int(end_page),
            }
        )

    if st.button("Merge first two chapters", key=f"merge_{book_id}", disabled=len(chapters) < 2):
        st.session_state[review_key] = _merge_first_two_chapters(chapters)
        st.rerun()

    first_chapter_can_split = bool(chapters) and int(chapters[0]["start_page"]) < int(
        chapters[0]["end_page"]
    )
    if st.button("Split first chapter", key=f"split_{book_id}", disabled=not first_chapter_can_split):
        st.session_state[review_key] = _split_first_chapter(chapters)
        st.rerun()

    if st.button("Save reviewed boundaries", key=f"save_boundaries_{book_id}"):
        with st.spinner("Saving chapter boundaries..."):
            review_result = save_chapter_boundaries_to_api(
                api_url,
                book_id=book_id,
                chapters=edited_chapters,
            )
        if review_result.success:
            st.success(review_result.message)
            st.markdown(review_result.message)
            st.markdown("Accepted chapter boundaries are saved for downstream lesson generation.")
            st.session_state[f"accepted_chapters_{book_id}"] = review_result.chapters
        else:
            st.error(review_result.message)
            st.markdown(review_result.message)
            if review_result.retryable:
                st.markdown("Adjust the boundaries and retry saving.")


def _render_summary_tab(*, api_url: str, books_result: object | None) -> None:
    accepted_chapters_by_book = _load_accepted_chapters_for_summary(
        api_url=api_url,
        books_result=books_result,
    )
    if not accepted_chapters_by_book:
        st.markdown("No generated chapter summary yet.")
        return

    for book, chapters in accepted_chapters_by_book:
        for chapter in chapters:
            chapter_number = int(chapter["chapter_number"])
            st.markdown(
                f"**{book['original_filename']} - "
                f"Chapter {chapter_number}: {chapter['title']}**"
            )
            result_key = f"summary_result_{book['id']}_{chapter_number}"
            if result_key not in st.session_state:
                loaded_result = get_chapter_summary_from_api(
                    api_url,
                    book_id=int(book["id"]),
                    chapter_number=chapter_number,
                )
                if loaded_result.success:
                    st.session_state[result_key] = loaded_result

            if st.button(
                f"Generate summary: {chapter_number}. {chapter['title']}",
                key=f"generate_summary_{book['id']}_{chapter_number}",
            ):
                with st.spinner("Generating cited summary..."):
                    summary_result = generate_chapter_summary_from_api(
                        api_url,
                        book_id=int(book["id"]),
                        chapter_number=chapter_number,
                    )
                st.session_state[result_key] = summary_result

            if result_key in st.session_state:
                _render_chapter_summary_result(
                    st.session_state[result_key],
                    api_url=api_url,
                    book_id=int(book["id"]),
                    chapter_number=chapter_number,
                )


def _render_core_concepts_tab(*, api_url: str, books_result: object | None) -> None:
    accepted_chapters_by_book = _load_accepted_chapters_for_summary(
        api_url=api_url,
        books_result=books_result,
    )
    if not accepted_chapters_by_book:
        st.markdown("No generated Core Concepts yet.")
        return

    for book, chapters in accepted_chapters_by_book:
        for chapter in chapters:
            chapter_number = int(chapter["chapter_number"])
            st.markdown(
                f"**{book['original_filename']} - "
                f"Chapter {chapter_number}: {chapter['title']}**"
            )
            result = _load_concepts_takeaways_result(
                api_url=api_url,
                book_id=int(book["id"]),
                chapter_number=chapter_number,
            )

            if st.button(
                f"Generate concepts and takeaways: {chapter_number}. {chapter['title']}",
                key=f"generate_concepts_takeaways_{book['id']}_{chapter_number}",
            ):
                with st.spinner("Generating Core Concepts and Key Takeaways..."):
                    result = generate_concepts_takeaways_from_api(
                        api_url,
                        book_id=int(book["id"]),
                        chapter_number=chapter_number,
                    )
                st.session_state[
                    f"concepts_takeaways_result_{book['id']}_{chapter_number}"
                ] = result

            if result is not None:
                _render_core_concepts_result(
                    result,
                    api_url=api_url,
                    book_id=int(book["id"]),
                    chapter_number=chapter_number,
                )


def _render_key_takeaways_tab(*, api_url: str, books_result: object | None) -> None:
    accepted_chapters_by_book = _load_accepted_chapters_for_summary(
        api_url=api_url,
        books_result=books_result,
    )
    if not accepted_chapters_by_book:
        st.markdown("No generated Key Takeaways yet.")
        return

    for book, chapters in accepted_chapters_by_book:
        for chapter in chapters:
            chapter_number = int(chapter["chapter_number"])
            result = _load_concepts_takeaways_result(
                api_url=api_url,
                book_id=int(book["id"]),
                chapter_number=chapter_number,
            )
            if result is None:
                st.markdown("Generate Core Concepts and Key Takeaways to see takeaways.")
            else:
                _render_key_takeaways_result(
                    result,
                    api_url=api_url,
                    book_id=int(book["id"]),
                    chapter_number=chapter_number,
                )


def _load_concepts_takeaways_result(
    *,
    api_url: str,
    book_id: int,
    chapter_number: int,
) -> object | None:
    result_key = f"concepts_takeaways_result_{book_id}_{chapter_number}"
    if result_key not in st.session_state:
        loaded_result = get_concepts_takeaways_from_api(
            api_url,
            book_id=book_id,
            chapter_number=chapter_number,
        )
        if loaded_result.success:
            st.session_state[result_key] = loaded_result

    return st.session_state.get(result_key)


def _render_core_concepts_result(
    result: object,
    *,
    api_url: str,
    book_id: int,
    chapter_number: int,
) -> None:
    if not result.success:
        st.error(result.message)
        st.markdown(result.message)
        if result.retryable:
            st.markdown("Retry Core Concepts and Key Takeaways generation for this chapter.")
        return

    st.success(result.message)
    st.markdown(result.message)
    for index, concept in enumerate((result.content or {}).get("core_concepts", []), start=1):
        st.markdown(f"**{concept['name']}**")
        st.markdown(concept["explanation"])
        st.markdown(concept["why_it_matters"])
        if concept.get("example"):
            st.markdown(concept["example"])
        _render_citation_controls(
            api_url=api_url,
            book_id=book_id,
            chapter_number=chapter_number,
            citation_ids=concept["citation_ids"],
            key_prefix=f"concept_{index}",
        )


def _render_key_takeaways_result(
    result: object,
    *,
    api_url: str,
    book_id: int,
    chapter_number: int,
) -> None:
    if not result.success:
        st.error(result.message)
        st.markdown(result.message)
        if result.retryable:
            st.markdown("Retry Core Concepts and Key Takeaways generation for this chapter.")
        return

    for index, takeaway in enumerate((result.content or {}).get("key_takeaways", []), start=1):
        st.markdown(f"- {takeaway['text']}")
        _render_citation_controls(
            api_url=api_url,
            book_id=book_id,
            chapter_number=chapter_number,
            citation_ids=takeaway["citation_ids"],
            key_prefix=f"takeaway_{index}",
        )


def _render_quiz_tab(*, api_url: str, books_result: object | None) -> None:
    accepted_chapters_by_book = _load_accepted_chapters_for_summary(
        api_url=api_url,
        books_result=books_result,
    )
    if not accepted_chapters_by_book:
        st.markdown("No generated Quiz yet.")
        return

    for book, chapters in accepted_chapters_by_book:
        for chapter in chapters:
            chapter_number = int(chapter["chapter_number"])
            st.markdown(
                f"**{book['original_filename']} - "
                f"Chapter {chapter_number}: {chapter['title']}**"
            )
            result = _load_quiz_result(
                api_url=api_url,
                book_id=int(book["id"]),
                chapter_number=chapter_number,
            )

            if st.button(
                f"Generate quiz: {chapter_number}. {chapter['title']}",
                key=f"generate_quiz_{book['id']}_{chapter_number}",
            ):
                with st.spinner("Generating five grounded quiz questions..."):
                    result = generate_quiz_from_api(
                        api_url,
                        book_id=int(book["id"]),
                        chapter_number=chapter_number,
                    )
                st.session_state[f"quiz_result_{book['id']}_{chapter_number}"] = result

            if result is not None:
                _render_quiz_result(
                    result,
                    api_url=api_url,
                    book_id=int(book["id"]),
                    chapter_number=chapter_number,
                )


def _load_quiz_result(
    *,
    api_url: str,
    book_id: int,
    chapter_number: int,
) -> object | None:
    result_key = f"quiz_result_{book_id}_{chapter_number}"
    if result_key not in st.session_state:
        loaded_result = get_quiz_from_api(
            api_url,
            book_id=book_id,
            chapter_number=chapter_number,
        )
        if loaded_result.success:
            st.session_state[result_key] = loaded_result

    return st.session_state.get(result_key)


def _render_quiz_result(
    result: object,
    *,
    api_url: str,
    book_id: int,
    chapter_number: int,
) -> None:
    if not result.success:
        st.error(result.message)
        st.markdown(result.message)
        if result.retryable:
            st.markdown("Retry quiz generation for this chapter.")
        return

    st.success(result.message)
    st.markdown(result.message)
    for index, question in enumerate((result.quiz or {}).get("questions", []), start=1):
        st.markdown(f"**Question {index}: {question['question_text']}**")
        st.markdown(f"Type: {question['question_type']}")
        st.markdown(f"Tested concept: {question['tested_concept']}")
        for option in question["answer_options"]:
            st.markdown(f"- {option}")
        _render_citation_controls(
            api_url=api_url,
            book_id=book_id,
            chapter_number=chapter_number,
            citation_ids=[question["citation_id"]],
            key_prefix=f"quiz_{index}",
        )


def _load_accepted_chapters_for_summary(
    *,
    api_url: str,
    books_result: object | None,
) -> list[tuple[dict[str, object], list[dict[str, object]]]]:
    if books_result is None or not getattr(books_result, "success", False):
        return []

    accepted_chapters_by_book = []
    for book in books_result.books:
        book_id = int(book["id"])
        accepted_key = f"accepted_chapters_{book_id}"
        chapters = st.session_state.get(accepted_key)
        if chapters is None and book.get("chapter_review_status") == "accepted":
            boundary_result = get_chapter_boundaries_from_api(api_url, book_id=book_id)
            if boundary_result.success:
                chapters = boundary_result.chapters
                st.session_state[accepted_key] = chapters
            else:
                st.error(boundary_result.message)
                if boundary_result.retryable:
                    st.markdown("Retry loading accepted chapter boundaries after FastAPI recovers.")
                chapters = []

        if chapters:
            accepted_chapters_by_book.append((book, chapters))

    return accepted_chapters_by_book


def _render_chapter_summary_result(
    result: object,
    *,
    api_url: str,
    book_id: int,
    chapter_number: int,
) -> None:
    if not result.success:
        st.error(result.message)
        st.markdown(result.message)
        if result.retryable:
            st.markdown("Retry summary generation for this chapter.")
        return

    st.success(result.message)
    st.markdown(result.message)
    summary = result.summary or {}
    central_argument = summary.get("central_argument", {})
    if central_argument:
        st.markdown(f"Central argument: {central_argument['claim']}")
        _render_citation_controls(
            api_url=api_url,
            book_id=book_id,
            chapter_number=chapter_number,
            citation_ids=central_argument["citation_ids"],
            key_prefix="central",
        )

    supporting_ideas = summary.get("supporting_ideas", [])
    if supporting_ideas:
        st.markdown("Supporting ideas")
        for index, idea in enumerate(supporting_ideas, start=1):
            st.markdown(f"- {idea['claim']}")
            _render_citation_controls(
                api_url=api_url,
                book_id=book_id,
                chapter_number=chapter_number,
                citation_ids=idea["citation_ids"],
                key_prefix=f"idea_{index}",
            )


def _render_citation_controls(
    *,
    api_url: str,
    book_id: int,
    chapter_number: int,
    citation_ids: list[str],
    key_prefix: str,
) -> None:
    for citation_id in citation_ids:
        if st.button(
            f"Citation {citation_id}",
            key=f"citation_{book_id}_{chapter_number}_{key_prefix}_{citation_id}",
        ):
            st.session_state["selected_evidence_request"] = {
                "book_id": book_id,
                "chapter_number": chapter_number,
                "citation_id": citation_id,
            }
            with st.spinner("Loading evidence..."):
                st.session_state["selected_evidence"] = get_citation_evidence_from_api(
                    api_url,
                    book_id=book_id,
                    chapter_number=chapter_number,
                    citation_id=citation_id,
                )


def _render_evidence_panel(*, api_url: str) -> None:
    evidence = st.session_state.get("selected_evidence")
    if evidence is None:
        st.markdown("Click a Summary citation to inspect its source excerpt.")
        return

    if not evidence.success:
        st.error(evidence.message)
        st.markdown(evidence.message)
        if evidence.retryable:
            request = st.session_state.get("selected_evidence_request")
            if st.button(f"Retry evidence {evidence.citation_id}", key="retry_evidence"):
                with st.spinner("Loading evidence..."):
                    st.session_state["selected_evidence"] = get_citation_evidence_from_api(
                        api_url,
                        book_id=int(request["book_id"]),
                        chapter_number=int(request["chapter_number"]),
                        citation_id=str(request["citation_id"]),
                    )
                evidence = st.session_state["selected_evidence"]
            else:
                st.markdown("Retry loading evidence after FastAPI is available.")
                return
        else:
            return

    if evidence.verification_status != "verified":
        st.warning("Unverified evidence")
        st.markdown(evidence.message)
        if evidence.source_location:
            st.markdown(f"Source location: {evidence.source_location}")
        if evidence.page_number:
            st.markdown(f"Page {evidence.page_number}")
        return

    st.markdown("Verified evidence")
    st.markdown(f"Citation {evidence.citation_id}")
    st.markdown(f"Source location: {evidence.source_location}")
    st.markdown(f"Page {evidence.page_number}")
    st.markdown(evidence.source_excerpt)


def _merge_first_two_chapters(chapters: list[dict[str, object]]) -> list[dict[str, object]]:
    if len(chapters) < 2:
        return chapters

    first, second, *rest = chapters
    merged = {
        **first,
        "chapter_number": 1,
        "title": f"{first['title']} / {second['title']}",
        "start_page": first["start_page"],
        "end_page": second["end_page"],
    }
    return _renumber_chapters([merged, *rest])


def _split_first_chapter(chapters: list[dict[str, object]]) -> list[dict[str, object]]:
    if not chapters:
        return chapters

    first, *rest = chapters
    start_page = int(first["start_page"])
    end_page = int(first["end_page"])
    if start_page >= end_page:
        return chapters

    split = [
        {**first, "chapter_number": 1, "end_page": start_page},
        {
            **first,
            "chapter_number": 2,
            "title": f"{first['title']} Part 2",
            "start_page": start_page + 1,
            "end_page": end_page,
        },
    ]
    return _renumber_chapters([*split, *rest])


def _renumber_chapters(chapters: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            **chapter,
            "chapter_number": index,
        }
        for index, chapter in enumerate(chapters, start=1)
    ]


if __name__ == "__main__":
    main()
