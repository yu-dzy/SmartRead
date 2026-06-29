import httpx

from smartread_frontend.uploads import (
    delete_uploaded_book_from_api,
    detect_chapters_from_api,
    extract_pdf_text_from_api,
    generate_chapter_summary_from_api,
    generate_concepts_takeaways_from_api,
    generate_quiz_from_api,
    get_chapter_boundaries_from_api,
    get_chapter_summary_from_api,
    get_citation_evidence_from_api,
    get_concepts_takeaways_from_api,
    get_dashboard_books_from_api,
    get_missed_concepts_from_api,
    get_quiz_progress_from_api,
    get_quiz_from_api,
    get_review_items_from_api,
    get_uploaded_books,
    retry_missed_question_to_api,
    save_chapter_boundaries_to_api,
    submit_review_item_answer_to_api,
    submit_quiz_answer_to_api,
    upload_pdf_to_api,
)


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def test_upload_pdf_to_api_sends_pdf_and_reports_success():
    captured_request: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["url"] = str(request.url)
        captured_request["content_type"] = request.headers["content-type"]
        return httpx.Response(
            201,
            json={
                "id": 1,
                "original_filename": "deep-work.pdf",
                "content_type": "application/pdf",
                "file_size": len(PDF_BYTES),
                "uploaded_at": "2026-06-27T12:00:00Z",
                "upload_status": "uploaded",
                "processing_status": "not_started",
                "error_message": None,
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = upload_pdf_to_api(
        "http://api.test",
        filename="deep-work.pdf",
        content=PDF_BYTES,
        content_type="application/pdf",
        client=client,
    )

    assert captured_request["method"] == "POST"
    assert captured_request["url"] == "http://api.test/books/uploads"
    assert captured_request["content_type"].startswith("multipart/form-data")
    assert result.success is True
    assert result.book is not None
    assert result.book["original_filename"] == "deep-work.pdf"
    assert result.message == "deep-work.pdf is ready in SmartRead."


def test_get_uploaded_books_returns_books_from_api():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "books": [
                    {
                        "id": 1,
                        "original_filename": "deep-work.pdf",
                        "content_type": "application/pdf",
                        "file_size": len(PDF_BYTES),
                        "uploaded_at": "2026-06-27T12:00:00Z",
                        "upload_status": "uploaded",
                        "processing_status": "not_started",
                        "error_message": None,
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_uploaded_books("http://api.test", client=client)

    assert result.success is True
    assert result.books[0]["original_filename"] == "deep-work.pdf"


def test_get_dashboard_books_from_api_returns_my_books_dashboard():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "http://api.test/dashboard/books"
        return httpx.Response(
            200,
            json={
                "books": [
                    {
                        "id": 7,
                        "title": "learning",
                        "author": None,
                        "original_filename": "learning.pdf",
                        "upload_status": "uploaded",
                        "analysis_status": "chapters_accepted",
                        "completed_chapter_count": 1,
                        "total_chapter_count": 2,
                        "latest_quiz_performance": {
                            "chapter_number": 1,
                            "answered_count": 5,
                            "correct_count": 4,
                            "incorrect_count": 1,
                            "total_questions": 5,
                            "score_percent": 80,
                        },
                        "chapter_mastery": {
                            "mastered_chapter_count": 0,
                            "chapter_count": 2,
                            "mastery_percent": 80,
                        },
                        "due_review_count": 1,
                        "continue_target": {
                            "type": "due_review",
                            "book_id": 7,
                            "chapter_number": 1,
                            "review_item_id": 3,
                            "tab": "Review",
                            "label": "Review Protected Attention",
                        },
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_dashboard_books_from_api("http://api.test", client=client)

    assert result.success is True
    assert result.books[0]["title"] == "learning"
    assert result.books[0]["due_review_count"] == 1


def test_get_dashboard_books_from_api_reports_recoverable_backend_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("backend down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_dashboard_books_from_api("http://api.test", client=client)

    assert result.success is False
    assert result.books == []
    assert result.retryable is True
    assert result.message == "My Books dashboard could not be loaded. Check FastAPI, then try again."


def test_delete_uploaded_book_from_api_reports_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert str(request.url) == "http://api.test/books/7"
        return httpx.Response(
            200,
            json={
                "deleted": True,
                "book_id": 7,
                "message": "Uploaded Book and related learning data were deleted.",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = delete_uploaded_book_from_api("http://api.test", book_id=7, client=client)

    assert result.success is True
    assert result.message == "Uploaded Book and related learning data were deleted."
    assert result.book_id == 7


def test_delete_uploaded_book_from_api_reports_recoverable_backend_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("backend down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = delete_uploaded_book_from_api("http://api.test", book_id=7, client=client)

    assert result.success is False
    assert result.retryable is True
    assert result.message == "Delete failed. Check FastAPI, then try again."


def test_upload_pdf_to_api_reports_retryable_backend_error():
    failed_book = {
        "id": 1,
        "original_filename": "empty.pdf",
        "content_type": "application/pdf",
        "file_size": 0,
        "uploaded_at": "2026-06-27T12:00:00Z",
        "upload_status": "failed",
        "processing_status": "not_started",
        "error_message": "The PDF could not be read. Upload a valid PDF and try again.",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "detail": {
                    "message": failed_book["error_message"],
                    "retryable": True,
                    "book": failed_book,
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = upload_pdf_to_api(
        "http://api.test",
        filename="empty.pdf",
        content=b"",
        content_type="application/pdf",
        client=client,
    )

    assert result.success is False
    assert result.message == "The PDF could not be read. Upload a valid PDF and try again."
    assert result.retryable is True
    assert result.book == failed_book


def test_extract_pdf_text_from_api_reports_extraction_summary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://api.test/books/7/extraction"
        return httpx.Response(
            200,
            json={
                "book": {
                    "id": 7,
                    "original_filename": "learning.pdf",
                    "content_type": "application/pdf",
                    "file_size": 100,
                    "uploaded_at": "2026-06-27T12:00:00Z",
                    "upload_status": "uploaded",
                    "processing_status": "extracted",
                    "error_message": None,
                },
                "summary": {
                    "page_count": 2,
                    "text_page_count": 2,
                    "blank_page_count": 0,
                },
                "pages": [
                    {
                        "book_id": 7,
                        "page_number": 1,
                        "source_location": "book:7:page:1",
                        "extracted_text": "First page",
                    }
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = extract_pdf_text_from_api("http://api.test", book_id=7, client=client)

    assert result.success is True
    assert result.message == "Extraction complete: 2 pages, 2 with text, 0 blank."
    assert result.summary["page_count"] == 2


def test_extract_pdf_text_from_api_reports_retryable_failure():
    failed_book = {
        "id": 7,
        "original_filename": "corrupt.pdf",
        "content_type": "application/pdf",
        "file_size": 100,
        "uploaded_at": "2026-06-27T12:00:00Z",
        "upload_status": "uploaded",
        "processing_status": "extraction_failed",
        "error_message": "Text extraction failed. Retry extraction or upload a cleaner PDF.",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "detail": {
                    "message": failed_book["error_message"],
                    "retryable": True,
                    "book": failed_book,
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = extract_pdf_text_from_api("http://api.test", book_id=7, client=client)

    assert result.success is False
    assert result.message == "Text extraction failed. Retry extraction or upload a cleaner PDF."
    assert result.retryable is True
    assert result.book == failed_book


def test_detect_chapters_from_api_reports_book_map_summary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://api.test/books/7/chapter-detection"
        return httpx.Response(
            200,
            json={
                "book": {
                    "id": 7,
                    "original_filename": "learning.pdf",
                    "content_type": "application/pdf",
                    "file_size": 100,
                    "uploaded_at": "2026-06-27T12:00:00Z",
                    "upload_status": "uploaded",
                    "processing_status": "extracted",
                    "error_message": None,
                    "chapter_detection_status": "detected",
                    "chapter_detection_confidence": "high",
                    "chapter_detection_message": None,
                },
                "summary": {
                    "chapter_count": 2,
                    "confidence": "high",
                    "warning": None,
                },
                "chapters": [
                    {
                        "book_id": 7,
                        "chapter_number": 1,
                        "title": "Getting Started",
                        "start_page": 1,
                        "end_page": 3,
                        "start_source_location": "book:7:page:1",
                        "end_source_location": "book:7:page:3",
                        "confidence": "high",
                        "detection_source": "heading_pattern",
                    }
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = detect_chapters_from_api("http://api.test", book_id=7, client=client)

    assert result.success is True
    assert result.message == "Detected 2 chapters with high confidence."
    assert result.summary["chapter_count"] == 2
    assert result.chapters[0]["title"] == "Getting Started"


def test_save_chapter_boundaries_to_api_reports_accepted_boundaries():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert str(request.url) == "http://api.test/books/7/chapter-boundaries"
        return httpx.Response(
            200,
            json={
                "book": {
                    "id": 7,
                    "original_filename": "learning.pdf",
                    "content_type": "application/pdf",
                    "file_size": 100,
                    "uploaded_at": "2026-06-27T12:00:00Z",
                    "upload_status": "uploaded",
                    "processing_status": "extracted",
                    "error_message": None,
                    "chapter_detection_status": "detected",
                    "chapter_detection_confidence": "high",
                    "chapter_detection_message": None,
                    "chapter_review_status": "accepted",
                },
                "chapters": [
                    {
                        "book_id": 7,
                        "chapter_number": 1,
                        "title": "Deep Focus",
                        "start_page": 1,
                        "end_page": 2,
                        "start_source_location": "book:7:page:1",
                        "end_source_location": "book:7:page:2",
                        "review_status": "accepted",
                    }
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = save_chapter_boundaries_to_api(
        "http://api.test",
        book_id=7,
        chapters=[
            {"chapter_number": 1, "title": "Deep Focus", "start_page": 1, "end_page": 2},
        ],
        client=client,
    )

    assert result.success is True
    assert result.message == "Accepted 1 reviewed chapter boundary."
    assert result.chapters[0]["title"] == "Deep Focus"


def test_save_chapter_boundaries_to_api_reports_retryable_validation_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={"detail": "Accepted chapter boundaries cannot overlap."},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = save_chapter_boundaries_to_api(
        "http://api.test",
        book_id=7,
        chapters=[
            {"chapter_number": 1, "title": "Focus", "start_page": 1, "end_page": 2},
            {"chapter_number": 2, "title": "Recall", "start_page": 2, "end_page": 2},
        ],
        client=client,
    )

    assert result.success is False
    assert result.message == "Accepted chapter boundaries cannot overlap."
    assert result.retryable is True


def test_get_chapter_boundaries_from_api_returns_accepted_chapters():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "http://api.test/books/7/chapter-boundaries"
        return httpx.Response(
            200,
            json={
                "chapters": [
                    {
                        "book_id": 7,
                        "chapter_number": 1,
                        "title": "Deep Focus",
                        "start_page": 1,
                        "end_page": 2,
                        "start_source_location": "book:7:page:1",
                        "end_source_location": "book:7:page:2",
                        "review_status": "accepted",
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_chapter_boundaries_from_api("http://api.test", book_id=7, client=client)

    assert result.success is True
    assert result.chapters[0]["title"] == "Deep Focus"


def test_generate_chapter_summary_from_api_reports_persisted_summary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://api.test/books/7/chapter-boundaries/1/summary"
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "chapter": {
                    "book_id": 7,
                    "chapter_number": 1,
                    "title": "Deep Focus",
                    "start_page": 1,
                    "end_page": 2,
                    "start_source_location": "book:7:page:1",
                    "end_source_location": "book:7:page:2",
                    "review_status": "accepted",
                },
                "generation_status": "generated",
                "generation_error": None,
                "provider": "openai",
                "model": "gpt-5.5",
                "generated_at": "2026-06-28T07:00:00Z",
                "summary": {
                    "central_argument": {
                        "claim": "Focus improves when attention is protected.",
                        "citation_ids": ["c1"],
                    },
                    "supporting_ideas": [],
                    "citations": [
                        {
                            "id": "c1",
                            "source_location": "book:7:page:1",
                            "page_number": 1,
                            "source_excerpt": "Focus improves when attention is protected.",
                        }
                    ],
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = generate_chapter_summary_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        client=client,
    )

    assert result.success is True
    assert result.message == "Summary generated for Chapter 1: Deep Focus."
    assert result.summary is not None
    assert result.summary["central_argument"]["claim"] == "Focus improves when attention is protected."


def test_get_chapter_summary_from_api_loads_persisted_summary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "http://api.test/books/7/chapter-boundaries/1/summary"
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "chapter": {
                    "book_id": 7,
                    "chapter_number": 1,
                    "title": "Deep Focus",
                    "start_page": 1,
                    "end_page": 2,
                    "start_source_location": "book:7:page:1",
                    "end_source_location": "book:7:page:2",
                    "review_status": "accepted",
                },
                "generation_status": "generated",
                "generation_error": None,
                "provider": "openai",
                "model": "gpt-5.5",
                "generated_at": "2026-06-28T07:00:00Z",
                "summary": {
                    "central_argument": {
                        "claim": "Persisted focus summary.",
                        "citation_ids": ["c1"],
                    },
                    "supporting_ideas": [],
                    "citations": [],
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_chapter_summary_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        client=client,
    )

    assert result.success is True
    assert result.message == "Summary loaded for Chapter 1: Deep Focus."
    assert result.summary is not None
    assert result.summary["central_argument"]["claim"] == "Persisted focus summary."


def test_get_citation_evidence_from_api_reports_verified_excerpt():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert (
            str(request.url)
            == "http://api.test/books/7/chapter-boundaries/1/summary/citations/c1/evidence"
        )
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "citation_id": "c1",
                "verification_status": "verified",
                "message": "Citation c1 is verified.",
                "source_location": "book:7:page:1",
                "page_number": 1,
                "source_excerpt": "Focus improves when attention is protected.",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_citation_evidence_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        citation_id="c1",
        client=client,
    )

    assert result.success is True
    assert result.verification_status == "verified"
    assert result.page_number == 1
    assert result.source_excerpt == "Focus improves when attention is protected."


def test_get_citation_evidence_from_api_reports_unverified_missing_citation():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "citation_id": "bad-id",
                "verification_status": "unverified",
                "message": "Citation bad-id could not be verified.",
                "source_location": None,
                "page_number": None,
                "source_excerpt": None,
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_citation_evidence_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        citation_id="bad-id",
        client=client,
    )

    assert result.success is True
    assert result.verification_status == "unverified"
    assert result.message == "Citation bad-id could not be verified."
    assert result.source_excerpt is None


def test_get_citation_evidence_from_api_reports_retryable_loading_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("backend down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_citation_evidence_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        citation_id="c1",
        client=client,
    )

    assert result.success is False
    assert result.retryable is True
    assert result.message == "Evidence could not be loaded. Check the FastAPI backend, then try again."


def test_generate_concepts_takeaways_from_api_reports_persisted_content():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://api.test/books/7/chapter-boundaries/1/concepts-takeaways"
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "chapter": {
                    "book_id": 7,
                    "chapter_number": 1,
                    "title": "Deep Focus",
                    "start_page": 1,
                    "end_page": 2,
                    "start_source_location": "book:7:page:1",
                    "end_source_location": "book:7:page:2",
                    "review_status": "accepted",
                },
                "generation_status": "generated",
                "generation_error": None,
                "provider": "openai",
                "model": "gpt-5.5",
                "generated_at": "2026-06-28T07:00:00Z",
                "content": {
                    "core_concepts": [
                        {
                            "name": "Protected Attention",
                            "explanation": "Protected attention reduces switching.",
                            "why_it_matters": "It keeps deliberate practice on track.",
                            "example": None,
                            "citation_ids": ["c1"],
                        }
                    ],
                    "key_takeaways": [
                        {
                            "text": "Protect attention before difficult practice.",
                            "citation_ids": ["c1"],
                        }
                    ],
                    "citations": [
                        {
                            "id": "c1",
                            "source_location": "book:7:page:1",
                            "page_number": 1,
                            "source_excerpt": "Protected attention reduces switching.",
                        }
                    ],
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = generate_concepts_takeaways_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        client=client,
    )

    assert result.success is True
    assert result.message == "Core Concepts and Key Takeaways generated for Chapter 1: Deep Focus."
    assert result.content is not None
    assert result.content["core_concepts"][0]["name"] == "Protected Attention"


def test_get_concepts_takeaways_from_api_loads_persisted_content():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "http://api.test/books/7/chapter-boundaries/1/concepts-takeaways"
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "chapter": {
                    "book_id": 7,
                    "chapter_number": 1,
                    "title": "Deep Focus",
                    "start_page": 1,
                    "end_page": 2,
                    "start_source_location": "book:7:page:1",
                    "end_source_location": "book:7:page:2",
                    "review_status": "accepted",
                },
                "generation_status": "generated",
                "generation_error": None,
                "provider": "openai",
                "model": "gpt-5.5",
                "generated_at": "2026-06-28T07:00:00Z",
                "content": {
                    "core_concepts": [
                        {
                            "name": "Protected Attention",
                            "explanation": "Protected attention reduces switching.",
                            "why_it_matters": "It keeps deliberate practice on track.",
                            "example": None,
                            "citation_ids": ["c1"],
                        }
                    ],
                    "key_takeaways": [
                        {
                            "text": "Protect attention before difficult practice.",
                            "citation_ids": ["c1"],
                        }
                    ],
                    "citations": [],
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_concepts_takeaways_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        client=client,
    )

    assert result.success is True
    assert result.message == "Core Concepts and Key Takeaways loaded for Chapter 1: Deep Focus."
    assert result.content is not None
    assert result.content["key_takeaways"][0]["text"] == "Protect attention before difficult practice."


def test_generate_quiz_from_api_reports_five_saved_questions():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://api.test/books/7/chapter-boundaries/1/quiz"
        return httpx.Response(200, json=_quiz_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = generate_quiz_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        client=client,
    )

    assert result.success is True
    assert result.message == "Quiz generated for Chapter 1: Deep Focus."
    assert result.quiz is not None
    assert len(result.quiz["questions"]) == 5
    assert result.quiz["questions"][0]["tested_concept"] == "Protected Attention"


def test_get_quiz_from_api_loads_saved_questions():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "http://api.test/books/7/chapter-boundaries/1/quiz"
        return httpx.Response(200, json=_quiz_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_quiz_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        client=client,
    )

    assert result.success is True
    assert result.message == "Quiz loaded for Chapter 1: Deep Focus."
    assert result.quiz is not None
    assert result.quiz["questions"][0]["question_text"] == (
        "What does protected attention reduce during deliberate practice?"
    )


def test_submit_quiz_answer_to_api_reports_immediate_feedback():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert (
            str(request.url)
            == "http://api.test/books/7/chapter-boundaries/1/quiz/answers/q1"
        )
        assert request.read() == b'{"selected_answer":"Long-term memory"}'
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "question_id": "q1",
                "selected_answer": "Long-term memory",
                "is_correct": False,
                "correct_answer": "Constant switching",
                "explanation": "Protected attention reduces constant switching.",
                "tested_concept": "Protected Attention",
                "citation_id": "qc1",
                "source_location": "book:7:page:1",
                "page_number": 1,
                "source_excerpt": "Protected attention reduces constant switching.",
                "progress": {
                    "answered_count": 1,
                    "correct_count": 0,
                    "incorrect_count": 1,
                    "total_questions": 5,
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = submit_quiz_answer_to_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        question_id="q1",
        selected_answer="Long-term memory",
        client=client,
    )

    assert result.success is True
    assert result.is_correct is False
    assert result.correct_answer == "Constant switching"
    assert result.tested_concept == "Protected Attention"
    assert result.source_excerpt == "Protected attention reduces constant switching."
    assert result.progress["incorrect_count"] == 1


def test_submit_quiz_answer_to_api_reports_recoverable_backend_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("backend down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = submit_quiz_answer_to_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        question_id="q1",
        selected_answer="Long-term memory",
        client=client,
    )

    assert result.success is False
    assert result.retryable is True
    assert result.message == "Answer feedback failed. Check the FastAPI backend, then try again."


def test_get_quiz_progress_from_api_loads_saved_answers():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "http://api.test/books/7/chapter-boundaries/1/quiz/progress"
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "progress": {
                    "answered_count": 1,
                    "correct_count": 1,
                    "incorrect_count": 0,
                    "total_questions": 5,
                },
                "answers": [
                    {
                        "book_id": 7,
                        "chapter_number": 1,
                        "question_id": "q1",
                        "selected_answer": "Constant switching",
                        "is_correct": True,
                        "correct_answer": "Constant switching",
                        "explanation": "Protected attention reduces constant switching.",
                        "tested_concept": "Protected Attention",
                        "citation_id": "qc1",
                        "source_location": "book:7:page:1",
                        "page_number": 1,
                        "source_excerpt": "Protected attention reduces constant switching.",
                        "progress": {
                            "answered_count": 1,
                            "correct_count": 1,
                            "incorrect_count": 0,
                            "total_questions": 5,
                        },
                    }
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_quiz_progress_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        client=client,
    )

    assert result.success is True
    assert result.progress["answered_count"] == 1
    assert result.answers[0]["question_id"] == "q1"
    assert result.answers[0]["is_correct"] is True


def test_get_missed_concepts_from_api_loads_saved_review_items():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert (
            str(request.url)
            == "http://api.test/books/7/chapter-boundaries/1/missed-concepts"
        )
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "summary": {"missed_concept_count": 1},
                "missed_concepts": [
                    {
                        "book_id": 7,
                        "chapter_number": 1,
                        "concept_name": "Protected Attention",
                        "question_id": "q1",
                        "quiz_answer_id": 3,
                        "explanation": "Protected attention reduces constant switching.",
                        "citation_id": "qc1",
                        "source_location": "book:7:page:1",
                        "page_number": 1,
                        "source_excerpt": "Protected attention reduces constant switching.",
                    }
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_missed_concepts_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        client=client,
    )

    assert result.success is True
    assert result.summary == {"missed_concept_count": 1}
    assert result.missed_concepts[0]["concept_name"] == "Protected Attention"
    assert result.missed_concepts[0]["source_excerpt"] == (
        "Protected attention reduces constant switching."
    )


def test_get_missed_concepts_from_api_reports_recoverable_loading_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("backend down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_missed_concepts_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        client=client,
    )

    assert result.success is False
    assert result.retryable is True
    assert result.message == "Missed Concepts could not be loaded. Check FastAPI, then try again."


def test_get_review_items_from_api_loads_due_and_upcoming_reviews():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert (
            str(request.url)
            == "http://api.test/books/7/chapter-boundaries/1/review-items"
        )
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "summary": {"due_review_count": 1, "active_review_count": 2},
                "review_items": [
                    {
                        "id": 1,
                        "missed_concept_id": 3,
                        "book_id": 7,
                        "chapter_number": 1,
                        "concept_name": "Protected Attention",
                        "question_id": "q1",
                        "stage": "day_1",
                        "due_on": "2026-06-29",
                        "status": "active",
                        "review_focus": "Protected attention reduces constant switching.",
                        "citation_id": "qc1",
                        "source_location": "book:7:page:1",
                        "page_number": 1,
                        "source_excerpt": "Protected attention reduces constant switching.",
                    }
                ],
                "upcoming_review_items": [
                    {
                        "id": 2,
                        "missed_concept_id": 4,
                        "book_id": 7,
                        "chapter_number": 1,
                        "concept_name": "Retrieval Cues",
                        "question_id": "q2",
                        "stage": "day_3",
                        "due_on": "2026-07-02",
                        "status": "active",
                        "review_focus": "Retrieval cues help recall.",
                        "citation_id": "qc2",
                        "source_location": "book:7:page:2",
                        "page_number": 2,
                        "source_excerpt": "Retrieval cues help recall.",
                    }
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_review_items_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        client=client,
    )

    assert result.success is True
    assert result.summary == {"due_review_count": 1, "active_review_count": 2}
    assert result.review_items[0]["concept_name"] == "Protected Attention"
    assert result.upcoming_review_items[0]["stage"] == "day_3"


def test_get_review_items_from_api_reports_recoverable_loading_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("backend down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = get_review_items_from_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        client=client,
    )

    assert result.success is False
    assert result.retryable is True
    assert result.message == "Review queue could not be loaded. Check FastAPI, then try again."


def test_submit_review_item_answer_to_api_reports_advanced_feedback():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert (
            str(request.url)
            == "http://api.test/books/7/chapter-boundaries/1/review-items/3/answer"
        )
        assert request.read() == b'{"selected_answer":"Constant switching"}'
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "question_id": "q1",
                "selected_answer": "Constant switching",
                "is_correct": True,
                "correct_answer": "Constant switching",
                "explanation": "Protected attention reduces constant switching.",
                "tested_concept": "Protected Attention",
                "citation_id": "qc1",
                "source_location": "book:7:page:1",
                "page_number": 1,
                "source_excerpt": "Protected attention reduces constant switching.",
                "progress": {},
                "review_result_status": "advanced",
                "review_item": {
                    "id": 3,
                    "missed_concept_id": 9,
                    "book_id": 7,
                    "chapter_number": 1,
                    "concept_name": "Protected Attention",
                    "question_id": "q1",
                    "stage": "day_3",
                    "due_on": "2026-07-02",
                    "status": "active",
                    "review_focus": "Protected attention reduces constant switching.",
                    "citation_id": "qc1",
                    "source_location": "book:7:page:1",
                    "page_number": 1,
                    "source_excerpt": "Protected attention reduces constant switching.",
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = submit_review_item_answer_to_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        review_item_id=3,
        selected_answer="Constant switching",
        client=client,
    )

    assert result.success is True
    assert result.message == "Review advanced."
    assert result.is_correct is True
    assert result.review_result_status == "advanced"
    assert result.review_item["stage"] == "day_3"


def test_submit_review_item_answer_to_api_reports_recoverable_backend_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("backend down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = submit_review_item_answer_to_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        review_item_id=3,
        selected_answer="Constant switching",
        client=client,
    )

    assert result.success is False
    assert result.retryable is True
    assert result.message == "Review feedback failed. Check FastAPI, then try again."


def test_retry_missed_question_to_api_reports_resolved_feedback():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert (
            str(request.url)
            == "http://api.test/books/7/chapter-boundaries/1/missed-concepts/q1/retry"
        )
        assert request.read() == b'{"selected_answer":"Constant switching"}'
        return httpx.Response(
            200,
            json={
                "book_id": 7,
                "chapter_number": 1,
                "question_id": "q1",
                "selected_answer": "Constant switching",
                "is_correct": True,
                "correct_answer": "Constant switching",
                "explanation": "Protected attention reduces constant switching.",
                "tested_concept": "Protected Attention",
                "citation_id": "qc1",
                "source_location": "book:7:page:1",
                "page_number": 1,
                "source_excerpt": "Protected attention reduces constant switching.",
                "progress": {
                    "answered_count": 1,
                    "correct_count": 1,
                    "incorrect_count": 0,
                    "total_questions": 5,
                },
                "missed_concept_status": "resolved",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = retry_missed_question_to_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        question_id="q1",
        selected_answer="Constant switching",
        client=client,
    )

    assert result.success is True
    assert result.is_correct is True
    assert result.missed_concept_status == "resolved"
    assert result.progress["correct_count"] == 1


def test_retry_missed_question_to_api_reports_recoverable_backend_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("backend down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = retry_missed_question_to_api(
        "http://api.test",
        book_id=7,
        chapter_number=1,
        question_id="q1",
        selected_answer="Constant switching",
        client=client,
    )

    assert result.success is False
    assert result.retryable is True
    assert result.message == "Retry failed. Check the FastAPI backend, then try again."


def _quiz_payload() -> dict[str, object]:
    return {
        "book_id": 7,
        "chapter_number": 1,
        "chapter": {
            "book_id": 7,
            "chapter_number": 1,
            "title": "Deep Focus",
            "start_page": 1,
            "end_page": 2,
            "start_source_location": "book:7:page:1",
            "end_source_location": "book:7:page:2",
            "review_status": "accepted",
        },
        "generation_status": "generated",
        "generation_error": None,
        "provider": "openai",
        "model": "gpt-5.5",
        "generated_at": "2026-06-28T07:00:00Z",
        "quiz": {
            "questions": [
                {
                    "id": "q1",
                    "question_text": (
                        "What does protected attention reduce during deliberate practice?"
                    ),
                    "question_type": "multiple_choice",
                    "answer_options": [
                        "Constant switching",
                        "Long-term memory",
                        "Chapter boundaries",
                    ],
                    "correct_answer": "Constant switching",
                    "explanation": "Protected attention reduces constant switching.",
                    "tested_concept": "Protected Attention",
                    "citation_id": "qc1",
                },
                {
                    "id": "q2",
                    "question_text": "True or false: retrieval cues help recall.",
                    "question_type": "true_false",
                    "answer_options": ["True", "False"],
                    "correct_answer": "True",
                    "explanation": "Retrieval cues help learners recall ideas.",
                    "tested_concept": "Retrieval Cues",
                    "citation_id": "qc2",
                },
                {
                    "id": "q3",
                    "question_text": "Which concept applies when a learner silences chat?",
                    "question_type": "scenario_application",
                    "answer_options": ["Protected Attention", "Retrieval Cues"],
                    "correct_answer": "Protected Attention",
                    "explanation": "Silencing chat protects attention.",
                    "tested_concept": "Protected Attention",
                    "citation_id": "qc1",
                },
                {
                    "id": "q4",
                    "question_text": "Which practice connects ideas to memory?",
                    "question_type": "multiple_choice",
                    "answer_options": ["Retrieval cues", "Ignoring feedback"],
                    "correct_answer": "Retrieval cues",
                    "explanation": "Retrieval cues connect practice to memory.",
                    "tested_concept": "Retrieval Cues",
                    "citation_id": "qc2",
                },
                {
                    "id": "q5",
                    "question_text": "What makes deliberate practice easier to repeat?",
                    "question_type": "multiple_choice",
                    "answer_options": ["Reducing context switching", "Removing citations"],
                    "correct_answer": "Reducing context switching",
                    "explanation": "Protected blocks reduce context switching.",
                    "tested_concept": "Protected Attention",
                    "citation_id": "qc1",
                },
            ],
            "citations": [
                {
                    "id": "qc1",
                    "source_location": "book:7:page:1",
                    "page_number": 1,
                    "source_excerpt": "Protected attention reduces constant switching.",
                },
                {
                    "id": "qc2",
                    "source_location": "book:7:page:2",
                    "page_number": 2,
                    "source_excerpt": "Retrieval cues help learners recall ideas.",
                },
            ],
        },
    }
