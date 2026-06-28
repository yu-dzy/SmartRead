from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from smartread_api.chapter_concepts import (
    ConceptsTakeawaysGenerationError,
    ConceptsTakeawaysGenerator,
    ConceptsTakeawaysValidationError,
    validate_concepts_takeaways_output,
)
from smartread_api.chapter_quizzes import (
    ChapterQuizGenerationError,
    ChapterQuizGenerator,
    ChapterQuizValidationError,
    validate_quiz_output,
)
from smartread_api.chapter_summaries import (
    ChapterSummaryGenerationError,
    ChapterSummaryGenerator,
    ChapterSummaryValidationError,
    validate_chapter_summary_output,
)


class UploadedBookNotFoundError(Exception):
    pass


class PdfExtractionError(Exception):
    def __init__(self, message: str, book: dict[str, Any]) -> None:
        super().__init__(message)
        self.message = message
        self.book = book


class ChapterBoundaryValidationError(Exception):
    pass


class AcceptedChapterNotFoundError(Exception):
    pass


class ChapterSummaryNotFoundError(Exception):
    pass


class ConceptsTakeawaysNotFoundError(Exception):
    pass


class ChapterQuizNotFoundError(Exception):
    pass


class QuizQuestionNotFoundError(Exception):
    pass


class QuizAnswerValidationError(Exception):
    pass


class MissedQuestionNotFoundError(Exception):
    pass


class ReviewItemNotFoundError(Exception):
    pass


CHAPTER_HEADING_PATTERN = re.compile(
    r"^\s*(?:chapter|ch\.?)\s+(?P<label>[0-9ivxlcdm]+)\s*[:.\-]?\s*(?P<title>.+)?$",
    re.IGNORECASE,
)
WEAK_NUMBERED_HEADING_PATTERN = re.compile(
    r"^\s*(?P<label>\d{1,2})[.)]\s+(?P<title>[A-Z][A-Za-z0-9 '&,\-]+)\s*$"
)


class UploadedBookStore:
    def __init__(
        self,
        database_path: str | Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.clock = clock or (lambda: datetime.now(UTC))
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save_uploaded_pdf(
        self,
        *,
        original_filename: str,
        content_type: str,
        content: bytes,
    ) -> dict[str, Any]:
        return self._save_pdf_metadata(
            original_filename=original_filename,
            content_type=content_type,
            content=content,
            upload_status="uploaded",
            processing_status="not_started",
            error_message=None,
        )

    def save_failed_pdf(
        self,
        *,
        original_filename: str,
        content_type: str,
        content: bytes,
        error_message: str,
    ) -> dict[str, Any]:
        return self._save_pdf_metadata(
            original_filename=original_filename,
            content_type=content_type,
            content=content,
            upload_status="failed",
            processing_status="not_started",
            error_message=error_message,
        )

    def list_uploaded_books(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM uploaded_books ORDER BY uploaded_at DESC, id DESC"
            ).fetchall()

        return [self._to_uploaded_book(row) for row in rows]

    def extract_pages_for_book(self, book_id: int) -> dict[str, Any]:
        with self._connect() as connection:
            book_row = connection.execute(
                "SELECT * FROM uploaded_books WHERE id = ?",
                (book_id,),
            ).fetchone()

        if book_row is None:
            raise UploadedBookNotFoundError

        pdf_content = book_row["pdf_content"]
        if not pdf_content:
            book = self._mark_extraction_failed(
                book_id,
                "The saved PDF could not be found. Upload the PDF again and retry extraction.",
            )
            raise PdfExtractionError(book["error_message"], book)

        try:
            pages = self._extract_pdf_pages(book_id, pdf_content)
        except Exception:
            book = self._mark_extraction_failed(
                book_id,
                "Text extraction failed. Retry extraction or upload a cleaner PDF.",
            )
            raise PdfExtractionError(book["error_message"], book) from None

        with self._connect() as connection:
            connection.execute("DELETE FROM source_pages WHERE book_id = ?", (book_id,))
            connection.executemany(
                """
                INSERT INTO source_pages (
                    book_id,
                    page_number,
                    source_location,
                    extracted_text
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        page["book_id"],
                        page["page_number"],
                        page["source_location"],
                        page["extracted_text"],
                    )
                    for page in pages
                ],
            )
            connection.execute(
                """
                UPDATE uploaded_books
                SET processing_status = ?, error_message = ?
                WHERE id = ?
                """,
                ("extracted", None, book_id),
            )
            book_row = connection.execute(
                "SELECT * FROM uploaded_books WHERE id = ?",
                (book_id,),
            ).fetchone()

        return {
            "book": self._to_uploaded_book(book_row),
            "summary": self._build_extraction_summary(pages),
            "pages": pages,
        }

    def list_pages_for_book(self, book_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            book_row = connection.execute(
                "SELECT id FROM uploaded_books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if book_row is None:
                raise UploadedBookNotFoundError

            rows = connection.execute(
                """
                SELECT book_id, page_number, source_location, extracted_text
                FROM source_pages
                WHERE book_id = ?
                ORDER BY page_number
                """,
                (book_id,),
            ).fetchall()

        return [self._to_source_page(row) for row in rows]

    def detect_chapters_for_book(self, book_id: int) -> dict[str, Any]:
        with self._connect() as connection:
            book_row = connection.execute(
                "SELECT * FROM uploaded_books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if book_row is None:
                raise UploadedBookNotFoundError

            page_rows = connection.execute(
                """
                SELECT book_id, page_number, source_location, extracted_text
                FROM source_pages
                WHERE book_id = ?
                ORDER BY page_number
                """,
                (book_id,),
            ).fetchall()

        pages = [self._to_source_page(row) for row in page_rows]
        chapters = self._detect_chapters_from_outline(book_id, book_row["pdf_content"], pages)
        if not chapters:
            chapters = self._detect_chapters_from_pages(book_id, pages)
        summary = self._build_chapter_detection_summary(chapters)

        with self._connect() as connection:
            connection.execute("DELETE FROM detected_chapters WHERE book_id = ?", (book_id,))
            connection.executemany(
                """
                INSERT INTO detected_chapters (
                    book_id,
                    chapter_number,
                    title,
                    start_page,
                    end_page,
                    start_source_location,
                    end_source_location,
                    confidence,
                    detection_source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chapter["book_id"],
                        chapter["chapter_number"],
                        chapter["title"],
                        chapter["start_page"],
                        chapter["end_page"],
                        chapter["start_source_location"],
                        chapter["end_source_location"],
                        chapter["confidence"],
                        chapter["detection_source"],
                    )
                    for chapter in chapters
                ],
            )
            connection.execute(
                """
                UPDATE uploaded_books
                SET chapter_detection_status = ?,
                    chapter_detection_confidence = ?,
                    chapter_detection_message = ?
                WHERE id = ?
                """,
                (
                    "detected" if chapters else "not_detected",
                    summary["confidence"],
                    summary["warning"],
                    book_id,
                ),
            )
            book_row = connection.execute(
                "SELECT * FROM uploaded_books WHERE id = ?",
                (book_id,),
            ).fetchone()

        return {
            "book": self._to_uploaded_book(book_row),
            "summary": summary,
            "chapters": chapters,
        }

    def list_chapters_for_book(self, book_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            book_row = connection.execute(
                "SELECT id FROM uploaded_books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if book_row is None:
                raise UploadedBookNotFoundError

            rows = connection.execute(
                """
                SELECT
                    book_id,
                    chapter_number,
                    title,
                    start_page,
                    end_page,
                    start_source_location,
                    end_source_location,
                    confidence,
                    detection_source
                FROM detected_chapters
                WHERE book_id = ?
                ORDER BY chapter_number
                """,
                (book_id,),
            ).fetchall()

        return [self._to_detected_chapter(row) for row in rows]

    def save_accepted_chapter_boundaries(
        self,
        book_id: int,
        chapters: list[dict[str, Any]],
    ) -> dict[str, Any]:
        with self._connect() as connection:
            book_row = connection.execute(
                "SELECT * FROM uploaded_books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if book_row is None:
                raise UploadedBookNotFoundError

            page_numbers = {
                row["page_number"]
                for row in connection.execute(
                    "SELECT page_number FROM source_pages WHERE book_id = ?",
                    (book_id,),
                ).fetchall()
            }

        accepted_chapters = self._build_accepted_chapters(
            book_id=book_id,
            chapters=chapters,
            page_numbers=page_numbers,
        )

        with self._connect() as connection:
            connection.execute("DELETE FROM accepted_chapters WHERE book_id = ?", (book_id,))
            connection.executemany(
                """
                INSERT INTO accepted_chapters (
                    book_id,
                    chapter_number,
                    title,
                    start_page,
                    end_page,
                    start_source_location,
                    end_source_location,
                    review_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chapter["book_id"],
                        chapter["chapter_number"],
                        chapter["title"],
                        chapter["start_page"],
                        chapter["end_page"],
                        chapter["start_source_location"],
                        chapter["end_source_location"],
                        chapter["review_status"],
                    )
                    for chapter in accepted_chapters
                ],
            )
            connection.execute(
                """
                UPDATE uploaded_books
                SET chapter_review_status = ?
                WHERE id = ?
                """,
                ("accepted", book_id),
            )
            book_row = connection.execute(
                "SELECT * FROM uploaded_books WHERE id = ?",
                (book_id,),
            ).fetchone()

        return {
            "book": self._to_uploaded_book(book_row),
            "chapters": accepted_chapters,
        }

    def list_accepted_chapter_boundaries(self, book_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            book_row = connection.execute(
                "SELECT id FROM uploaded_books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if book_row is None:
                raise UploadedBookNotFoundError

            rows = connection.execute(
                """
                SELECT
                    book_id,
                    chapter_number,
                    title,
                    start_page,
                    end_page,
                    start_source_location,
                    end_source_location,
                    review_status
                FROM accepted_chapters
                WHERE book_id = ?
                ORDER BY chapter_number
                """,
                (book_id,),
            ).fetchall()

        return [self._to_accepted_chapter(row) for row in rows]

    def get_accepted_chapter_source_pages(
        self,
        book_id: int,
        chapter_number: int,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            chapter_row = connection.execute(
                """
                SELECT
                    book_id,
                    chapter_number,
                    title,
                    start_page,
                    end_page,
                    start_source_location,
                    end_source_location,
                    review_status
                FROM accepted_chapters
                WHERE book_id = ? AND chapter_number = ?
                """,
                (book_id, chapter_number),
            ).fetchone()
            if chapter_row is None:
                raise AcceptedChapterNotFoundError

            chapter = self._to_accepted_chapter(chapter_row)
            page_rows = connection.execute(
                """
                SELECT book_id, page_number, source_location, extracted_text
                FROM source_pages
                WHERE book_id = ?
                  AND page_number >= ?
                  AND page_number <= ?
                ORDER BY page_number
                """,
                (book_id, chapter["start_page"], chapter["end_page"]),
            ).fetchall()

        return {
            "chapter": chapter,
            "pages": [self._to_source_page(row) for row in page_rows],
        }

    def generate_chapter_summary(
        self,
        book_id: int,
        chapter_number: int,
        generator: ChapterSummaryGenerator,
    ) -> dict[str, Any]:
        source = self.get_accepted_chapter_source_pages(book_id, chapter_number)
        chapter = source["chapter"]
        pages = source["pages"]

        try:
            generated_output = generator.generate_summary(chapter=chapter, pages=pages)
            summary = validate_chapter_summary_output(generated_output, pages=pages)
        except ChapterSummaryGenerationError as error:
            return self._save_failed_chapter_summary(
                book_id=book_id,
                chapter_number=chapter_number,
                chapter=chapter,
                provider=getattr(generator, "provider", "unknown"),
                model=getattr(generator, "model", "unknown"),
                error_message=error.message,
            )
        except ChapterSummaryValidationError as error:
            return self._save_failed_chapter_summary(
                book_id=book_id,
                chapter_number=chapter_number,
                chapter=chapter,
                provider=getattr(generator, "provider", "unknown"),
                model=getattr(generator, "model", "unknown"),
                error_message=error.message,
            )

        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chapter_summaries (
                    book_id,
                    chapter_number,
                    generation_status,
                    generation_error,
                    provider,
                    model,
                    generated_at,
                    summary_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(book_id, chapter_number)
                DO UPDATE SET
                    generation_status = excluded.generation_status,
                    generation_error = excluded.generation_error,
                    provider = excluded.provider,
                    model = excluded.model,
                    generated_at = excluded.generated_at,
                    summary_json = excluded.summary_json
                """,
                (
                    book_id,
                    chapter_number,
                    "generated",
                    None,
                    getattr(generator, "provider", "unknown"),
                    getattr(generator, "model", "unknown"),
                    generated_at,
                    json.dumps(summary),
                ),
            )

        return self.get_chapter_summary(book_id, chapter_number)

    def get_chapter_summary(self, book_id: int, chapter_number: int) -> dict[str, Any]:
        source = self.get_accepted_chapter_source_pages(book_id, chapter_number)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    book_id,
                    chapter_number,
                    generation_status,
                    generation_error,
                    provider,
                    model,
                    generated_at,
                    summary_json
                FROM chapter_summaries
                WHERE book_id = ? AND chapter_number = ?
                """,
                (book_id, chapter_number),
            ).fetchone()

        if row is None:
            raise ChapterSummaryNotFoundError

        return self._to_chapter_summary(row, source["chapter"])

    def get_chapter_summary_citation_evidence(
        self,
        book_id: int,
        chapter_number: int,
        citation_id: str,
    ) -> dict[str, Any]:
        current_source = self.get_accepted_chapter_source_pages(book_id, chapter_number)
        current_pages_by_location = {
            page["source_location"]: page for page in current_source["pages"]
        }
        generated_content = []
        try:
            summary_record = self.get_chapter_summary(book_id, chapter_number)
            generated_content.append(summary_record["summary"] or {})
        except ChapterSummaryNotFoundError:
            pass

        try:
            concepts_record = self.get_chapter_concepts_takeaways(book_id, chapter_number)
            generated_content.append(concepts_record["content"] or {})
        except ConceptsTakeawaysNotFoundError:
            pass

        try:
            quiz_record = self.get_chapter_quiz(book_id, chapter_number)
            generated_content.append(quiz_record["quiz"] or {})
        except ChapterQuizNotFoundError:
            pass

        if not generated_content:
            raise ChapterSummaryNotFoundError

        for content in generated_content:
            evidence = self._resolve_citation_evidence_from_content(
                content=content,
                book_id=book_id,
                chapter_number=chapter_number,
                citation_id=citation_id,
                current_pages_by_location=current_pages_by_location,
            )
            if evidence is not None:
                return evidence

        return self._build_unverified_citation_evidence(
            book_id=book_id,
            chapter_number=chapter_number,
            citation_id=citation_id,
            message=f"Citation {citation_id} could not be verified.",
        )

    def generate_chapter_concepts_takeaways(
        self,
        book_id: int,
        chapter_number: int,
        generator: ConceptsTakeawaysGenerator,
    ) -> dict[str, Any]:
        source = self.get_accepted_chapter_source_pages(book_id, chapter_number)
        chapter = source["chapter"]
        pages = source["pages"]

        try:
            generated_output = generator.generate_concepts_takeaways(
                chapter=chapter,
                pages=pages,
            )
            content = validate_concepts_takeaways_output(generated_output, pages=pages)
        except ConceptsTakeawaysGenerationError as error:
            return self._save_failed_concepts_takeaways(
                book_id=book_id,
                chapter_number=chapter_number,
                chapter=chapter,
                provider=getattr(generator, "provider", "unknown"),
                model=getattr(generator, "model", "unknown"),
                error_message=error.message,
            )
        except ConceptsTakeawaysValidationError as error:
            return self._save_failed_concepts_takeaways(
                book_id=book_id,
                chapter_number=chapter_number,
                chapter=chapter,
                provider=getattr(generator, "provider", "unknown"),
                model=getattr(generator, "model", "unknown"),
                error_message=error.message,
            )

        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chapter_concepts_takeaways (
                    book_id,
                    chapter_number,
                    generation_status,
                    generation_error,
                    provider,
                    model,
                    generated_at,
                    content_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(book_id, chapter_number)
                DO UPDATE SET
                    generation_status = excluded.generation_status,
                    generation_error = excluded.generation_error,
                    provider = excluded.provider,
                    model = excluded.model,
                    generated_at = excluded.generated_at,
                    content_json = excluded.content_json
                """,
                (
                    book_id,
                    chapter_number,
                    "generated",
                    None,
                    getattr(generator, "provider", "unknown"),
                    getattr(generator, "model", "unknown"),
                    generated_at,
                    json.dumps(content),
                ),
            )

        return self.get_chapter_concepts_takeaways(book_id, chapter_number)

    def get_chapter_concepts_takeaways(
        self,
        book_id: int,
        chapter_number: int,
    ) -> dict[str, Any]:
        source = self.get_accepted_chapter_source_pages(book_id, chapter_number)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    book_id,
                    chapter_number,
                    generation_status,
                    generation_error,
                    provider,
                    model,
                    generated_at,
                    content_json
                FROM chapter_concepts_takeaways
                WHERE book_id = ? AND chapter_number = ?
                """,
                (book_id, chapter_number),
            ).fetchone()

        if row is None:
            raise ConceptsTakeawaysNotFoundError

        return self._to_chapter_concepts_takeaways(row, source["chapter"])

    def generate_chapter_quiz(
        self,
        book_id: int,
        chapter_number: int,
        generator: ChapterQuizGenerator,
    ) -> dict[str, Any]:
        source = self.get_accepted_chapter_source_pages(book_id, chapter_number)
        chapter = source["chapter"]
        pages = source["pages"]
        concepts_record = self.get_chapter_concepts_takeaways(book_id, chapter_number)
        core_concepts = (concepts_record["content"] or {}).get("core_concepts", [])

        try:
            generated_output = generator.generate_quiz(
                chapter=chapter,
                pages=pages,
                core_concepts=core_concepts,
            )
            quiz = validate_quiz_output(
                generated_output,
                pages=pages,
                core_concepts=core_concepts,
            )
        except ChapterQuizGenerationError as error:
            return self._save_failed_chapter_quiz(
                book_id=book_id,
                chapter_number=chapter_number,
                chapter=chapter,
                provider=getattr(generator, "provider", "unknown"),
                model=getattr(generator, "model", "unknown"),
                error_message=error.message,
            )
        except ChapterQuizValidationError as error:
            return self._save_failed_chapter_quiz(
                book_id=book_id,
                chapter_number=chapter_number,
                chapter=chapter,
                provider=getattr(generator, "provider", "unknown"),
                model=getattr(generator, "model", "unknown"),
                error_message=error.message,
            )

        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chapter_quizzes (
                    book_id,
                    chapter_number,
                    generation_status,
                    generation_error,
                    provider,
                    model,
                    generated_at,
                    quiz_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(book_id, chapter_number)
                DO UPDATE SET
                    generation_status = excluded.generation_status,
                    generation_error = excluded.generation_error,
                    provider = excluded.provider,
                    model = excluded.model,
                    generated_at = excluded.generated_at,
                    quiz_json = excluded.quiz_json
                """,
                (
                    book_id,
                    chapter_number,
                    "generated",
                    None,
                    getattr(generator, "provider", "unknown"),
                    getattr(generator, "model", "unknown"),
                    generated_at,
                    json.dumps(quiz),
                ),
            )

        return self.get_chapter_quiz(book_id, chapter_number)

    def get_chapter_quiz(
        self,
        book_id: int,
        chapter_number: int,
    ) -> dict[str, Any]:
        source = self.get_accepted_chapter_source_pages(book_id, chapter_number)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    book_id,
                    chapter_number,
                    generation_status,
                    generation_error,
                    provider,
                    model,
                    generated_at,
                    quiz_json
                FROM chapter_quizzes
                WHERE book_id = ? AND chapter_number = ?
                """,
                (book_id, chapter_number),
            ).fetchone()

        if row is None:
            raise ChapterQuizNotFoundError

        return self._to_chapter_quiz(row, source["chapter"])

    def submit_quiz_answer(
        self,
        book_id: int,
        chapter_number: int,
        question_id: str,
        selected_answer: str,
    ) -> dict[str, Any]:
        selected_answer = selected_answer.strip()
        if not selected_answer:
            raise QuizAnswerValidationError("Choose an answer before checking it.")

        quiz_record = self.get_chapter_quiz(book_id, chapter_number)
        quiz = quiz_record["quiz"] or {}
        question = self._find_quiz_question(quiz, question_id)
        if question is None:
            raise QuizQuestionNotFoundError
        if selected_answer not in question["answer_options"]:
            raise QuizAnswerValidationError("Choose one of the saved answer options.")

        citation = self._find_quiz_citation(quiz, question["citation_id"])
        is_correct = self._normalize_answer(selected_answer) == self._normalize_answer(
            question["correct_answer"]
        )
        submitted_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO quiz_answers (
                    book_id,
                    chapter_number,
                    question_id,
                    selected_answer,
                    is_correct,
                    submitted_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(book_id, chapter_number, question_id)
                DO UPDATE SET
                    selected_answer = excluded.selected_answer,
                    is_correct = excluded.is_correct,
                    submitted_at = excluded.submitted_at
                """,
                (
                    book_id,
                    chapter_number,
                    question_id,
                    selected_answer,
                    int(is_correct),
                    submitted_at,
                ),
            )
            answer_row = self._fetch_quiz_answer_row(
                connection,
                book_id,
                chapter_number,
                question_id,
            )
            if not is_correct:
                self._save_missed_concept(
                    connection=connection,
                    book_id=book_id,
                    chapter_number=chapter_number,
                    question=question,
                    quiz_answer_id=answer_row["id"],
                    citation=citation,
                    created_at=submitted_at,
                )
            answer_rows = self._fetch_quiz_answer_rows(connection, book_id, chapter_number)

        return self._build_quiz_answer_feedback(
            book_id=book_id,
            chapter_number=chapter_number,
            question=question,
            selected_answer=selected_answer,
            is_correct=is_correct,
            citation=citation,
            progress=self._build_quiz_progress(answer_rows, total_questions=len(quiz["questions"])),
        )

    def list_missed_concepts(
        self,
        book_id: int,
        chapter_number: int,
    ) -> dict[str, Any]:
        self.get_accepted_chapter_source_pages(book_id, chapter_number)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    book_id,
                    chapter_number,
                    concept_name,
                    question_id,
                    quiz_answer_id,
                    explanation,
                    citation_id,
                    source_location,
                    page_number,
                    source_excerpt
                FROM missed_concepts
                WHERE book_id = ? AND chapter_number = ?
                ORDER BY concept_name
                """,
                (book_id, chapter_number),
            ).fetchall()

        missed_concepts = [self._to_missed_concept(row) for row in rows]
        return {
            "book_id": book_id,
            "chapter_number": chapter_number,
            "summary": {"missed_concept_count": len(missed_concepts)},
            "missed_concepts": missed_concepts,
        }

    def list_review_items(
        self,
        book_id: int,
        chapter_number: int,
    ) -> dict[str, Any]:
        self.get_accepted_chapter_source_pages(book_id, chapter_number)
        today = self._today_iso()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    review_items.id,
                    review_items.missed_concept_id,
                    review_items.book_id,
                    review_items.chapter_number,
                    review_items.concept_name,
                    review_items.question_id,
                    review_items.review_focus,
                    review_items.citation_id,
                    review_items.source_location,
                    review_items.page_number,
                    review_items.source_excerpt,
                    review_items.stage,
                    review_items.due_on,
                    review_items.status,
                    latest_result.selected_answer AS last_selected_answer,
                    latest_result.is_correct AS last_is_correct,
                    latest_result.previous_stage AS last_previous_stage,
                    latest_result.next_stage AS last_next_stage,
                    latest_result.result_status AS last_result_status,
                    latest_result.reviewed_at AS last_reviewed_at
                FROM review_items
                LEFT JOIN (
                    SELECT review_results.*
                    FROM review_results
                    INNER JOIN (
                        SELECT review_item_id, MAX(id) AS last_result_id
                        FROM review_results
                        GROUP BY review_item_id
                    ) latest
                        ON review_results.id = latest.last_result_id
                ) latest_result
                    ON latest_result.review_item_id = review_items.id
                WHERE review_items.book_id = ?
                  AND review_items.chapter_number = ?
                  AND review_items.status = 'active'
                ORDER BY review_items.due_on, review_items.concept_name
                """,
                (book_id, chapter_number),
            ).fetchall()

        review_items = [self._to_review_item(row) for row in rows]
        due_items = [item for item in review_items if item["due_on"] <= today]
        upcoming_items = [item for item in review_items if item["due_on"] > today]
        return {
            "book_id": book_id,
            "chapter_number": chapter_number,
            "summary": {
                "due_review_count": len(due_items),
                "active_review_count": len(review_items),
            },
            "review_items": due_items,
            "upcoming_review_items": upcoming_items,
        }

    def retry_missed_question(
        self,
        book_id: int,
        chapter_number: int,
        question_id: str,
        selected_answer: str,
    ) -> dict[str, Any]:
        selected_answer = selected_answer.strip()
        if not selected_answer:
            raise QuizAnswerValidationError("Choose an answer before retrying it.")

        quiz_record = self.get_chapter_quiz(book_id, chapter_number)
        quiz = quiz_record["quiz"] or {}
        question = self._find_quiz_question(quiz, question_id)
        if question is None:
            raise QuizQuestionNotFoundError
        if selected_answer not in question["answer_options"]:
            raise QuizAnswerValidationError("Choose one of the saved answer options.")

        citation = self._find_quiz_citation(quiz, question["citation_id"])
        is_correct = self._normalize_answer(selected_answer) == self._normalize_answer(
            question["correct_answer"]
        )
        submitted_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

        with self._connect() as connection:
            missed_concept = self._fetch_missed_concept_row(
                connection,
                book_id,
                chapter_number,
                question_id,
            )
            if missed_concept is None:
                raise MissedQuestionNotFoundError

            connection.execute(
                """
                INSERT INTO quiz_answers (
                    book_id,
                    chapter_number,
                    question_id,
                    selected_answer,
                    is_correct,
                    submitted_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(book_id, chapter_number, question_id)
                DO UPDATE SET
                    selected_answer = excluded.selected_answer,
                    is_correct = excluded.is_correct,
                    submitted_at = excluded.submitted_at
                """,
                (
                    book_id,
                    chapter_number,
                    question_id,
                    selected_answer,
                    int(is_correct),
                    submitted_at,
                ),
            )
            answer_row = self._fetch_quiz_answer_row(
                connection,
                book_id,
                chapter_number,
                question_id,
            )
            if is_correct:
                self._delete_missed_concept(
                    connection,
                    book_id,
                    chapter_number,
                    question_id,
                )
                missed_concept_status = "resolved"
            else:
                self._save_missed_concept(
                    connection=connection,
                    book_id=book_id,
                    chapter_number=chapter_number,
                    question=question,
                    quiz_answer_id=answer_row["id"],
                    citation=citation,
                    created_at=submitted_at,
                )
                missed_concept_status = "active"

            answer_rows = self._fetch_quiz_answer_rows(connection, book_id, chapter_number)

        feedback = self._build_quiz_answer_feedback(
            book_id=book_id,
            chapter_number=chapter_number,
            question=question,
            selected_answer=selected_answer,
            is_correct=is_correct,
            citation=citation,
            progress=self._build_quiz_progress(answer_rows, total_questions=len(quiz["questions"])),
        )
        return {**feedback, "missed_concept_status": missed_concept_status}

    def submit_review_item_answer(
        self,
        book_id: int,
        chapter_number: int,
        review_item_id: int,
        selected_answer: str,
    ) -> dict[str, Any]:
        selected_answer = selected_answer.strip()
        if not selected_answer:
            raise QuizAnswerValidationError("Choose an answer before checking this review.")

        quiz_record = self.get_chapter_quiz(book_id, chapter_number)
        quiz = quiz_record["quiz"] or {}

        with self._connect() as connection:
            review_item_row = self._fetch_review_item_row(
                connection,
                book_id,
                chapter_number,
                review_item_id,
            )
            if review_item_row is None:
                raise ReviewItemNotFoundError

            question = self._find_quiz_question(quiz, review_item_row["question_id"])
            if question is None:
                raise QuizQuestionNotFoundError
            if selected_answer not in question["answer_options"]:
                raise QuizAnswerValidationError("Choose one of the saved answer options.")

            citation = self._find_quiz_citation(quiz, question["citation_id"])
            is_correct = self._normalize_answer(selected_answer) == self._normalize_answer(
                question["correct_answer"]
            )
            previous_stage = review_item_row["stage"]
            next_stage, due_on, status, result_status = self._next_review_schedule(
                previous_stage=previous_stage,
                is_correct=is_correct,
            )
            reviewed_at = self._now().isoformat(timespec="seconds").replace("+00:00", "Z")
            connection.execute(
                """
                UPDATE review_items
                SET stage = ?,
                    due_on = ?,
                    status = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    next_stage,
                    due_on,
                    status,
                    reviewed_at,
                    reviewed_at if status == "completed" else None,
                    review_item_id,
                ),
            )
            self._save_review_result(
                connection=connection,
                review_item_id=review_item_id,
                selected_answer=selected_answer,
                is_correct=is_correct,
                previous_stage=previous_stage,
                next_stage=next_stage,
                result_status=result_status,
                reviewed_at=reviewed_at,
            )
            updated_review_item = self._fetch_review_item_row(
                connection,
                book_id,
                chapter_number,
                review_item_id,
                include_completed=True,
            )

        feedback = self._build_quiz_answer_feedback(
            book_id=book_id,
            chapter_number=chapter_number,
            question=question,
            selected_answer=selected_answer,
            is_correct=is_correct,
            citation=citation,
            progress={},
        )
        return {
            **feedback,
            "review_result_status": result_status,
            "review_item": self._to_review_item(updated_review_item),
        }

    def get_quiz_progress(
        self,
        book_id: int,
        chapter_number: int,
    ) -> dict[str, Any]:
        quiz_record = self.get_chapter_quiz(book_id, chapter_number)
        quiz = quiz_record["quiz"] or {}

        with self._connect() as connection:
            answer_rows = self._fetch_quiz_answer_rows(connection, book_id, chapter_number)

        progress = self._build_quiz_progress(answer_rows, total_questions=len(quiz["questions"]))
        answers = []
        for row in answer_rows:
            question = self._find_quiz_question(quiz, row["question_id"])
            if question is None:
                continue

            answers.append(
                self._build_quiz_answer_feedback(
                    book_id=book_id,
                    chapter_number=chapter_number,
                    question=question,
                    selected_answer=row["selected_answer"],
                    is_correct=bool(row["is_correct"]),
                    citation=self._find_quiz_citation(quiz, question["citation_id"]),
                    progress=progress,
                )
            )

        return {
            "book_id": book_id,
            "chapter_number": chapter_number,
            "progress": progress,
            "answers": answers,
        }

    def _save_pdf_metadata(
        self,
        *,
        original_filename: str,
        content_type: str,
        content: bytes,
        upload_status: str,
        processing_status: str,
        error_message: str | None,
    ) -> dict[str, Any]:
        file_size = len(content)
        content_sha256 = hashlib.sha256(content).hexdigest()
        uploaded_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO uploaded_books (
                        original_filename,
                        content_type,
                        file_size,
                        content_sha256,
                        pdf_content,
                        uploaded_at,
                        upload_status,
                        processing_status,
                        error_message
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        original_filename,
                        content_type,
                        file_size,
                        content_sha256,
                        content,
                        uploaded_at,
                        upload_status,
                        processing_status,
                        error_message,
                    ),
                )
                book_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                return self._find_by_fingerprint(
                    connection,
                    original_filename=original_filename,
                    file_size=file_size,
                    content_sha256=content_sha256,
                )

            row = connection.execute(
                "SELECT * FROM uploaded_books WHERE id = ?",
                (book_id,),
            ).fetchone()

        return self._to_uploaded_book(row)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS uploaded_books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL,
                    upload_status TEXT NOT NULL,
                    processing_status TEXT NOT NULL,
                    error_message TEXT,
                    pdf_content BLOB,
                    chapter_detection_status TEXT NOT NULL DEFAULT 'not_started',
                    chapter_detection_confidence TEXT,
                    chapter_detection_message TEXT,
                    chapter_review_status TEXT NOT NULL DEFAULT 'not_started',
                    UNIQUE(original_filename, file_size, content_sha256)
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(uploaded_books)").fetchall()
            }
            if "error_message" not in columns:
                connection.execute("ALTER TABLE uploaded_books ADD COLUMN error_message TEXT")
            if "pdf_content" not in columns:
                connection.execute("ALTER TABLE uploaded_books ADD COLUMN pdf_content BLOB")
            if "chapter_detection_status" not in columns:
                connection.execute(
                    """
                    ALTER TABLE uploaded_books
                    ADD COLUMN chapter_detection_status TEXT NOT NULL DEFAULT 'not_started'
                    """
                )
            if "chapter_detection_confidence" not in columns:
                connection.execute(
                    "ALTER TABLE uploaded_books ADD COLUMN chapter_detection_confidence TEXT"
                )
            if "chapter_detection_message" not in columns:
                connection.execute(
                    "ALTER TABLE uploaded_books ADD COLUMN chapter_detection_message TEXT"
                )
            if "chapter_review_status" not in columns:
                connection.execute(
                    """
                    ALTER TABLE uploaded_books
                    ADD COLUMN chapter_review_status TEXT NOT NULL DEFAULT 'not_started'
                    """
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS source_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    page_number INTEGER NOT NULL,
                    source_location TEXT NOT NULL,
                    extracted_text TEXT NOT NULL,
                    UNIQUE(book_id, page_number),
                    FOREIGN KEY(book_id) REFERENCES uploaded_books(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS accepted_chapters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    start_page INTEGER NOT NULL,
                    end_page INTEGER NOT NULL,
                    start_source_location TEXT NOT NULL,
                    end_source_location TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    UNIQUE(book_id, chapter_number),
                    FOREIGN KEY(book_id) REFERENCES uploaded_books(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS detected_chapters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    start_page INTEGER NOT NULL,
                    end_page INTEGER NOT NULL,
                    start_source_location TEXT NOT NULL,
                    end_source_location TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    detection_source TEXT NOT NULL,
                    UNIQUE(book_id, chapter_number),
                    FOREIGN KEY(book_id) REFERENCES uploaded_books(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chapter_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    generation_status TEXT NOT NULL,
                    generation_error TEXT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    generated_at TEXT,
                    summary_json TEXT,
                    UNIQUE(book_id, chapter_number),
                    FOREIGN KEY(book_id) REFERENCES uploaded_books(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chapter_concepts_takeaways (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    generation_status TEXT NOT NULL,
                    generation_error TEXT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    generated_at TEXT,
                    content_json TEXT,
                    UNIQUE(book_id, chapter_number),
                    FOREIGN KEY(book_id) REFERENCES uploaded_books(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chapter_quizzes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    generation_status TEXT NOT NULL,
                    generation_error TEXT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    generated_at TEXT,
                    quiz_json TEXT,
                    UNIQUE(book_id, chapter_number),
                    FOREIGN KEY(book_id) REFERENCES uploaded_books(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS quiz_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    question_id TEXT NOT NULL,
                    selected_answer TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    submitted_at TEXT NOT NULL,
                    UNIQUE(book_id, chapter_number, question_id),
                    FOREIGN KEY(book_id) REFERENCES uploaded_books(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS missed_concepts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    concept_name TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    quiz_answer_id INTEGER NOT NULL,
                    explanation TEXT NOT NULL,
                    citation_id TEXT NOT NULL,
                    source_location TEXT,
                    page_number INTEGER,
                    source_excerpt TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(book_id, chapter_number, concept_name),
                    FOREIGN KEY(book_id) REFERENCES uploaded_books(id),
                    FOREIGN KEY(quiz_answer_id) REFERENCES quiz_answers(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS review_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    missed_concept_id INTEGER NOT NULL,
                    book_id INTEGER NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    concept_name TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    review_focus TEXT NOT NULL,
                    citation_id TEXT NOT NULL,
                    source_location TEXT,
                    page_number INTEGER,
                    source_excerpt TEXT,
                    stage TEXT NOT NULL,
                    due_on TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(missed_concept_id),
                    FOREIGN KEY(missed_concept_id) REFERENCES missed_concepts(id),
                    FOREIGN KEY(book_id) REFERENCES uploaded_books(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS review_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    review_item_id INTEGER NOT NULL,
                    selected_answer TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    previous_stage TEXT NOT NULL,
                    next_stage TEXT NOT NULL,
                    result_status TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    FOREIGN KEY(review_item_id) REFERENCES review_items(id)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _find_by_fingerprint(
        self,
        connection: sqlite3.Connection,
        *,
        original_filename: str,
        file_size: int,
        content_sha256: str,
    ) -> dict[str, Any]:
        row = connection.execute(
            """
            SELECT * FROM uploaded_books
            WHERE original_filename = ?
              AND file_size = ?
              AND content_sha256 = ?
            """,
            (original_filename, file_size, content_sha256),
        ).fetchone()

        return self._to_uploaded_book(row)

    def _to_uploaded_book(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "original_filename": row["original_filename"],
            "content_type": row["content_type"],
            "file_size": row["file_size"],
            "uploaded_at": row["uploaded_at"],
            "upload_status": row["upload_status"],
            "processing_status": row["processing_status"],
            "error_message": row["error_message"],
            "chapter_detection_status": row["chapter_detection_status"],
            "chapter_detection_confidence": row["chapter_detection_confidence"],
            "chapter_detection_message": row["chapter_detection_message"],
            "chapter_review_status": row["chapter_review_status"],
        }

    def _to_source_page(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "book_id": row["book_id"],
            "page_number": row["page_number"],
            "source_location": row["source_location"],
            "extracted_text": row["extracted_text"],
        }

    def _to_detected_chapter(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "book_id": row["book_id"],
            "chapter_number": row["chapter_number"],
            "title": row["title"],
            "start_page": row["start_page"],
            "end_page": row["end_page"],
            "start_source_location": row["start_source_location"],
            "end_source_location": row["end_source_location"],
            "confidence": row["confidence"],
            "detection_source": row["detection_source"],
        }

    def _to_accepted_chapter(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "book_id": row["book_id"],
            "chapter_number": row["chapter_number"],
            "title": row["title"],
            "start_page": row["start_page"],
            "end_page": row["end_page"],
            "start_source_location": row["start_source_location"],
            "end_source_location": row["end_source_location"],
            "review_status": row["review_status"],
        }

    def _to_chapter_summary(
        self,
        row: sqlite3.Row,
        chapter: dict[str, Any],
    ) -> dict[str, Any]:
        summary_json = row["summary_json"]
        return {
            "book_id": row["book_id"],
            "chapter_number": row["chapter_number"],
            "chapter": chapter,
            "generation_status": row["generation_status"],
            "generation_error": row["generation_error"],
            "provider": row["provider"],
            "model": row["model"],
            "generated_at": row["generated_at"],
            "summary": json.loads(summary_json) if summary_json else None,
        }

    def _to_chapter_concepts_takeaways(
        self,
        row: sqlite3.Row,
        chapter: dict[str, Any],
    ) -> dict[str, Any]:
        content_json = row["content_json"]
        return {
            "book_id": row["book_id"],
            "chapter_number": row["chapter_number"],
            "chapter": chapter,
            "generation_status": row["generation_status"],
            "generation_error": row["generation_error"],
            "provider": row["provider"],
            "model": row["model"],
            "generated_at": row["generated_at"],
            "content": json.loads(content_json) if content_json else None,
        }

    def _to_chapter_quiz(
        self,
        row: sqlite3.Row,
        chapter: dict[str, Any],
    ) -> dict[str, Any]:
        quiz_json = row["quiz_json"]
        return {
            "book_id": row["book_id"],
            "chapter_number": row["chapter_number"],
            "chapter": chapter,
            "generation_status": row["generation_status"],
            "generation_error": row["generation_error"],
            "provider": row["provider"],
            "model": row["model"],
            "generated_at": row["generated_at"],
            "quiz": json.loads(quiz_json) if quiz_json else None,
        }

    def _to_missed_concept(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "book_id": row["book_id"],
            "chapter_number": row["chapter_number"],
            "concept_name": row["concept_name"],
            "question_id": row["question_id"],
            "quiz_answer_id": row["quiz_answer_id"],
            "explanation": row["explanation"],
            "citation_id": row["citation_id"],
            "source_location": row["source_location"],
            "page_number": row["page_number"],
            "source_excerpt": row["source_excerpt"],
        }

    def _to_review_item(self, row: sqlite3.Row) -> dict[str, Any]:
        review_item = {
            "id": row["id"],
            "missed_concept_id": row["missed_concept_id"],
            "book_id": row["book_id"],
            "chapter_number": row["chapter_number"],
            "concept_name": row["concept_name"],
            "question_id": row["question_id"],
            "stage": row["stage"],
            "due_on": row["due_on"],
            "status": row["status"],
            "review_focus": row["review_focus"],
            "citation_id": row["citation_id"],
            "source_location": row["source_location"],
            "page_number": row["page_number"],
            "source_excerpt": row["source_excerpt"],
        }
        if "last_selected_answer" in row.keys() and row["last_selected_answer"] is not None:
            review_item["last_review_result"] = {
                "selected_answer": row["last_selected_answer"],
                "is_correct": bool(row["last_is_correct"]),
                "previous_stage": row["last_previous_stage"],
                "next_stage": row["last_next_stage"],
                "result_status": row["last_result_status"],
                "reviewed_at": row["last_reviewed_at"],
            }

        return review_item

    def _find_quiz_question(
        self,
        quiz: dict[str, Any],
        question_id: str,
    ) -> dict[str, Any] | None:
        for question in quiz.get("questions", []):
            if question.get("id") == question_id:
                return question
        return None

    def _find_quiz_citation(
        self,
        quiz: dict[str, Any],
        citation_id: str,
    ) -> dict[str, Any] | None:
        for citation in quiz.get("citations", []):
            if citation.get("id") == citation_id:
                return citation
        return None

    def _fetch_quiz_answer_rows(
        self,
        connection: sqlite3.Connection,
        book_id: int,
        chapter_number: int,
    ) -> list[sqlite3.Row]:
        return connection.execute(
            """
            SELECT id, question_id, selected_answer, is_correct, submitted_at
            FROM quiz_answers
            WHERE book_id = ? AND chapter_number = ?
            ORDER BY submitted_at, question_id
            """,
            (book_id, chapter_number),
        ).fetchall()

    def _fetch_quiz_answer_row(
        self,
        connection: sqlite3.Connection,
        book_id: int,
        chapter_number: int,
        question_id: str,
    ) -> sqlite3.Row:
        return connection.execute(
            """
            SELECT id, question_id, selected_answer, is_correct, submitted_at
            FROM quiz_answers
            WHERE book_id = ? AND chapter_number = ? AND question_id = ?
            """,
            (book_id, chapter_number, question_id),
        ).fetchone()

    def _fetch_missed_concept_row(
        self,
        connection: sqlite3.Connection,
        book_id: int,
        chapter_number: int,
        question_id: str,
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT id, concept_name, question_id
            FROM missed_concepts
            WHERE book_id = ? AND chapter_number = ? AND question_id = ?
            """,
            (book_id, chapter_number, question_id),
        ).fetchone()

    def _delete_missed_concept(
        self,
        connection: sqlite3.Connection,
        book_id: int,
        chapter_number: int,
        question_id: str,
    ) -> None:
        resolved_at = self._now().isoformat(timespec="seconds").replace("+00:00", "Z")
        connection.execute(
            """
            UPDATE review_items
            SET status = ?,
                due_on = ?,
                updated_at = ?,
                completed_at = ?
            WHERE missed_concept_id IN (
                SELECT id
                FROM missed_concepts
                WHERE book_id = ? AND chapter_number = ? AND question_id = ?
            )
            """,
            ("resolved", None, resolved_at, resolved_at, book_id, chapter_number, question_id),
        )
        connection.execute(
            """
            DELETE FROM missed_concepts
            WHERE book_id = ? AND chapter_number = ? AND question_id = ?
            """,
            (book_id, chapter_number, question_id),
        )

    def _save_missed_concept(
        self,
        *,
        connection: sqlite3.Connection,
        book_id: int,
        chapter_number: int,
        question: dict[str, Any],
        quiz_answer_id: int,
        citation: dict[str, Any] | None,
        created_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO missed_concepts (
                book_id,
                chapter_number,
                concept_name,
                question_id,
                quiz_answer_id,
                explanation,
                citation_id,
                source_location,
                page_number,
                source_excerpt,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(book_id, chapter_number, concept_name)
            DO UPDATE SET
                question_id = excluded.question_id,
                quiz_answer_id = excluded.quiz_answer_id,
                explanation = excluded.explanation,
                citation_id = excluded.citation_id,
                source_location = excluded.source_location,
                page_number = excluded.page_number,
                source_excerpt = excluded.source_excerpt
            """,
            (
                book_id,
                chapter_number,
                question["tested_concept"],
                question["id"],
                quiz_answer_id,
                question["explanation"],
                question["citation_id"],
                citation["source_location"] if citation else None,
                citation["page_number"] if citation else None,
                citation["source_excerpt"] if citation else None,
                created_at,
            ),
        )
        missed_concept = connection.execute(
            """
            SELECT
                id,
                book_id,
                chapter_number,
                concept_name,
                question_id,
                explanation,
                citation_id,
                source_location,
                page_number,
                source_excerpt
            FROM missed_concepts
            WHERE book_id = ? AND chapter_number = ? AND concept_name = ?
            """,
            (book_id, chapter_number, question["tested_concept"]),
        ).fetchone()
        if missed_concept is not None:
            self._save_review_item_for_missed_concept(connection, missed_concept)

    def _fetch_review_item_row(
        self,
        connection: sqlite3.Connection,
        book_id: int,
        chapter_number: int,
        review_item_id: int,
        *,
        include_completed: bool = False,
    ) -> sqlite3.Row | None:
        status_filter = "" if include_completed else "AND status = 'active'"
        return connection.execute(
            f"""
            SELECT
                review_items.id,
                review_items.missed_concept_id,
                review_items.book_id,
                review_items.chapter_number,
                review_items.concept_name,
                review_items.question_id,
                review_items.review_focus,
                review_items.citation_id,
                review_items.source_location,
                review_items.page_number,
                review_items.source_excerpt,
                review_items.stage,
                review_items.due_on,
                review_items.status,
                latest_result.selected_answer AS last_selected_answer,
                latest_result.is_correct AS last_is_correct,
                latest_result.previous_stage AS last_previous_stage,
                latest_result.next_stage AS last_next_stage,
                latest_result.result_status AS last_result_status,
                latest_result.reviewed_at AS last_reviewed_at
            FROM review_items
            LEFT JOIN (
                SELECT review_results.*
                FROM review_results
                INNER JOIN (
                    SELECT review_item_id, MAX(id) AS last_result_id
                    FROM review_results
                    GROUP BY review_item_id
                ) latest
                    ON review_results.id = latest.last_result_id
            ) latest_result
                ON latest_result.review_item_id = review_items.id
            WHERE review_items.book_id = ?
              AND review_items.chapter_number = ?
              AND review_items.id = ?
            {status_filter}
            """,
            (book_id, chapter_number, review_item_id),
        ).fetchone()

    def _save_review_item_for_missed_concept(
        self,
        connection: sqlite3.Connection,
        missed_concept: sqlite3.Row,
    ) -> None:
        now = self._now()
        now_iso = now.isoformat(timespec="seconds").replace("+00:00", "Z")
        due_on = self._date_after_days(1)
        connection.execute(
            """
            INSERT INTO review_items (
                missed_concept_id,
                book_id,
                chapter_number,
                concept_name,
                question_id,
                review_focus,
                citation_id,
                source_location,
                page_number,
                source_excerpt,
                stage,
                due_on,
                status,
                created_at,
                updated_at,
                completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(missed_concept_id)
            DO UPDATE SET
                book_id = excluded.book_id,
                chapter_number = excluded.chapter_number,
                concept_name = excluded.concept_name,
                question_id = excluded.question_id,
                review_focus = excluded.review_focus,
                citation_id = excluded.citation_id,
                source_location = excluded.source_location,
                page_number = excluded.page_number,
                source_excerpt = excluded.source_excerpt,
                stage = excluded.stage,
                due_on = excluded.due_on,
                status = excluded.status,
                updated_at = excluded.updated_at,
                completed_at = NULL
            """,
            (
                missed_concept["id"],
                missed_concept["book_id"],
                missed_concept["chapter_number"],
                missed_concept["concept_name"],
                missed_concept["question_id"],
                missed_concept["explanation"],
                missed_concept["citation_id"],
                missed_concept["source_location"],
                missed_concept["page_number"],
                missed_concept["source_excerpt"],
                "day_1",
                due_on,
                "active",
                now_iso,
                now_iso,
                None,
            ),
        )

    def _save_review_result(
        self,
        *,
        connection: sqlite3.Connection,
        review_item_id: int,
        selected_answer: str,
        is_correct: bool,
        previous_stage: str,
        next_stage: str,
        result_status: str,
        reviewed_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO review_results (
                review_item_id,
                selected_answer,
                is_correct,
                previous_stage,
                next_stage,
                result_status,
                reviewed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_item_id,
                selected_answer,
                int(is_correct),
                previous_stage,
                next_stage,
                result_status,
                reviewed_at,
            ),
        )

    def _next_review_schedule(
        self,
        *,
        previous_stage: str,
        is_correct: bool,
    ) -> tuple[str, str | None, str, str]:
        if not is_correct:
            return "day_1", self._date_after_days(1), "active", "reset"

        if previous_stage == "day_1":
            return "day_3", self._date_after_days(3), "active", "advanced"
        if previous_stage == "day_3":
            return "day_7", self._date_after_days(7), "active", "advanced"

        return "day_7", None, "completed", "completed"

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None:
            return now.replace(tzinfo=UTC)
        return now.astimezone(UTC)

    def _today_iso(self) -> str:
        return self._now().date().isoformat()

    def _date_after_days(self, days: int) -> str:
        return (self._now().date() + timedelta(days=days)).isoformat()

    def _build_quiz_answer_feedback(
        self,
        *,
        book_id: int,
        chapter_number: int,
        question: dict[str, Any],
        selected_answer: str,
        is_correct: bool,
        citation: dict[str, Any] | None,
        progress: dict[str, int],
    ) -> dict[str, Any]:
        return {
            "book_id": book_id,
            "chapter_number": chapter_number,
            "question_id": question["id"],
            "selected_answer": selected_answer,
            "is_correct": is_correct,
            "correct_answer": question["correct_answer"],
            "explanation": question["explanation"],
            "tested_concept": question["tested_concept"],
            "citation_id": question["citation_id"],
            "source_location": citation["source_location"] if citation else None,
            "page_number": citation["page_number"] if citation else None,
            "source_excerpt": citation["source_excerpt"] if citation else None,
            "progress": progress,
        }

    def _build_quiz_progress(
        self,
        answer_rows: list[sqlite3.Row],
        *,
        total_questions: int,
    ) -> dict[str, int]:
        correct_count = sum(1 for row in answer_rows if bool(row["is_correct"]))
        answered_count = len(answer_rows)
        return {
            "answered_count": answered_count,
            "correct_count": correct_count,
            "incorrect_count": answered_count - correct_count,
            "total_questions": total_questions,
        }

    def _normalize_answer(self, answer: str) -> str:
        return " ".join(answer.strip().casefold().split())

    def _save_failed_chapter_summary(
        self,
        *,
        book_id: int,
        chapter_number: int,
        chapter: dict[str, Any],
        provider: str,
        model: str,
        error_message: str,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chapter_summaries (
                    book_id,
                    chapter_number,
                    generation_status,
                    generation_error,
                    provider,
                    model,
                    generated_at,
                    summary_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(book_id, chapter_number)
                DO UPDATE SET
                    generation_status = excluded.generation_status,
                    generation_error = excluded.generation_error,
                    provider = excluded.provider,
                    model = excluded.model,
                    generated_at = excluded.generated_at,
                    summary_json = excluded.summary_json
                """,
                (
                    book_id,
                    chapter_number,
                    "failed",
                    error_message,
                    provider,
                    model,
                    None,
                    None,
                ),
            )

        return {
            "book_id": book_id,
            "chapter_number": chapter_number,
            "chapter": chapter,
            "generation_status": "failed",
            "generation_error": error_message,
            "provider": provider,
            "model": model,
            "generated_at": None,
            "summary": None,
        }

    def _save_failed_concepts_takeaways(
        self,
        *,
        book_id: int,
        chapter_number: int,
        chapter: dict[str, Any],
        provider: str,
        model: str,
        error_message: str,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chapter_concepts_takeaways (
                    book_id,
                    chapter_number,
                    generation_status,
                    generation_error,
                    provider,
                    model,
                    generated_at,
                    content_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(book_id, chapter_number)
                DO UPDATE SET
                    generation_status = excluded.generation_status,
                    generation_error = excluded.generation_error,
                    provider = excluded.provider,
                    model = excluded.model,
                    generated_at = excluded.generated_at,
                    content_json = excluded.content_json
                """,
                (
                    book_id,
                    chapter_number,
                    "failed",
                    error_message,
                    provider,
                    model,
                    None,
                    None,
                ),
            )

        return {
            "book_id": book_id,
            "chapter_number": chapter_number,
            "chapter": chapter,
            "generation_status": "failed",
            "generation_error": error_message,
            "provider": provider,
            "model": model,
            "generated_at": None,
            "content": None,
        }

    def _save_failed_chapter_quiz(
        self,
        *,
        book_id: int,
        chapter_number: int,
        chapter: dict[str, Any],
        provider: str,
        model: str,
        error_message: str,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chapter_quizzes (
                    book_id,
                    chapter_number,
                    generation_status,
                    generation_error,
                    provider,
                    model,
                    generated_at,
                    quiz_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(book_id, chapter_number)
                DO UPDATE SET
                    generation_status = excluded.generation_status,
                    generation_error = excluded.generation_error,
                    provider = excluded.provider,
                    model = excluded.model,
                    generated_at = excluded.generated_at,
                    quiz_json = excluded.quiz_json
                """,
                (
                    book_id,
                    chapter_number,
                    "failed",
                    error_message,
                    provider,
                    model,
                    None,
                    None,
                ),
            )

        return {
            "book_id": book_id,
            "chapter_number": chapter_number,
            "chapter": chapter,
            "generation_status": "failed",
            "generation_error": error_message,
            "provider": provider,
            "model": model,
            "generated_at": None,
            "quiz": None,
        }

    def _resolve_citation_evidence_from_content(
        self,
        *,
        content: dict[str, Any],
        book_id: int,
        chapter_number: int,
        citation_id: str,
        current_pages_by_location: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        for citation in content.get("citations", []):
            if citation.get("id") != citation_id:
                continue

            source_location = citation["source_location"]
            page_number = citation["page_number"]
            current_page = current_pages_by_location.get(source_location)
            if current_page is None or current_page["page_number"] != page_number:
                return self._build_unverified_citation_evidence(
                    book_id=book_id,
                    chapter_number=chapter_number,
                    citation_id=citation_id,
                    message=(
                        f"Citation {citation_id} no longer points inside "
                        "the accepted chapter boundary."
                    ),
                    source_location=source_location,
                    page_number=page_number,
                )

            source_excerpt = citation.get("source_excerpt")
            if not source_excerpt:
                return self._build_unverified_citation_evidence(
                    book_id=book_id,
                    chapter_number=chapter_number,
                    citation_id=citation_id,
                    message=f"Citation {citation_id} is missing a source excerpt.",
                    source_location=source_location,
                    page_number=page_number,
                )

            return {
                "book_id": book_id,
                "chapter_number": chapter_number,
                "citation_id": citation_id,
                "verification_status": "verified",
                "message": f"Citation {citation_id} is verified.",
                "source_location": source_location,
                "page_number": page_number,
                "source_excerpt": source_excerpt,
            }

        return None

    def _build_unverified_citation_evidence(
        self,
        *,
        book_id: int,
        chapter_number: int,
        citation_id: str,
        message: str,
        source_location: str | None = None,
        page_number: int | None = None,
    ) -> dict[str, Any]:
        return {
            "book_id": book_id,
            "chapter_number": chapter_number,
            "citation_id": citation_id,
            "verification_status": "unverified",
            "message": message,
            "source_location": source_location,
            "page_number": page_number,
            "source_excerpt": None,
        }

    def _extract_pdf_pages(self, book_id: int, pdf_content: bytes) -> list[dict[str, Any]]:
        reader = PdfReader(BytesIO(pdf_content))
        pages: list[dict[str, Any]] = []

        for page_index, page in enumerate(reader.pages, start=1):
            extracted_text = (page.extract_text() or "").strip()
            pages.append(
                {
                    "book_id": book_id,
                    "page_number": page_index,
                    "source_location": f"book:{book_id}:page:{page_index}",
                    "extracted_text": extracted_text,
                }
            )

        return pages

    def _detect_chapters_from_outline(
        self,
        book_id: int,
        pdf_content: bytes | None,
        pages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not pdf_content or not pages:
            return []

        try:
            reader = PdfReader(BytesIO(pdf_content))
            starts = self._collect_outline_starts(reader, {page["page_number"] for page in pages})
        except Exception:
            return []

        return self._build_chapters_from_starts(
            book_id=book_id,
            starts=starts,
            last_page=pages[-1]["page_number"],
            detection_source="pdf_outline",
        )

    def _mark_extraction_failed(self, book_id: int, message: str) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE uploaded_books
                SET processing_status = ?, error_message = ?
                WHERE id = ?
                """,
                ("extraction_failed", message, book_id),
            )
            row = connection.execute(
                "SELECT * FROM uploaded_books WHERE id = ?",
                (book_id,),
            ).fetchone()

        return self._to_uploaded_book(row)

    def _build_extraction_summary(self, pages: list[dict[str, Any]]) -> dict[str, int]:
        text_page_count = sum(1 for page in pages if page["extracted_text"])
        return {
            "page_count": len(pages),
            "text_page_count": text_page_count,
            "blank_page_count": len(pages) - text_page_count,
        }

    def _detect_chapters_from_pages(
        self,
        book_id: int,
        pages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        headings = []
        for page in pages:
            first_lines = [
                line.strip()
                for line in page["extracted_text"].splitlines()[:4]
                if line.strip()
            ]
            for line in first_lines:
                match = CHAPTER_HEADING_PATTERN.match(line)
                weak_match = WEAK_NUMBERED_HEADING_PATTERN.match(line) if match is None else None
                if match is not None:
                    raw_title = (match.group("title") or "").strip()
                    title = raw_title or f"Chapter {match.group('label')}"
                    confidence = "high"
                    detection_source = "heading_pattern"
                elif weak_match is not None:
                    title = weak_match.group("title").strip()
                    confidence = "low"
                    detection_source = "numbered_heading_pattern"
                else:
                    continue

                headings.append(
                    {
                        "title": title,
                        "page_number": page["page_number"],
                        "source_location": page["source_location"],
                        "confidence": confidence,
                        "detection_source": detection_source,
                    }
                )
                break

        if not headings:
            return []

        return self._build_chapters_from_starts(
            book_id=book_id,
            starts=headings,
            last_page=pages[-1]["page_number"],
        )

    def _collect_outline_starts(
        self,
        reader: PdfReader,
        valid_page_numbers: set[int],
    ) -> list[dict[str, Any]]:
        starts: list[dict[str, Any]] = []
        seen_pages: set[int] = set()

        def walk(items: list[Any]) -> None:
            for item in items:
                if isinstance(item, list):
                    walk(item)
                    continue

                title = str(getattr(item, "title", "")).strip()
                if not title:
                    continue

                page_number = reader.get_destination_page_number(item) + 1
                if page_number not in valid_page_numbers or page_number in seen_pages:
                    continue

                seen_pages.add(page_number)
                starts.append(
                    {
                        "title": title,
                        "page_number": page_number,
                        "source_location": f"book:pending:page:{page_number}",
                        "confidence": "high",
                        "detection_source": "pdf_outline",
                    }
                )

        walk(reader.outline)
        return sorted(starts, key=lambda start: start["page_number"])

    def _build_chapters_from_starts(
        self,
        *,
        book_id: int,
        starts: list[dict[str, Any]],
        last_page: int,
        detection_source: str | None = None,
    ) -> list[dict[str, Any]]:
        chapters = []
        for index, start in enumerate(starts):
            next_start = starts[index + 1] if index + 1 < len(starts) else None
            end_page = (next_start["page_number"] - 1) if next_start else last_page
            source = detection_source or start["detection_source"]
            confidence = "high" if len(starts) >= 2 and start["confidence"] == "high" else "low"
            chapters.append(
                {
                    "book_id": book_id,
                    "chapter_number": index + 1,
                    "title": start["title"],
                    "start_page": start["page_number"],
                    "end_page": end_page,
                    "start_source_location": f"book:{book_id}:page:{start['page_number']}",
                    "end_source_location": f"book:{book_id}:page:{end_page}",
                    "confidence": confidence,
                    "detection_source": source,
                }
            )

        return chapters

    def _build_chapter_detection_summary(
        self,
        chapters: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not chapters:
            return {
                "chapter_count": 0,
                "confidence": "none",
                "warning": "No chapters could be detected. Manual chapter review will be required.",
            }

        confidence = "low" if any(chapter["confidence"] == "low" for chapter in chapters) else "high"
        return {
            "chapter_count": len(chapters),
            "confidence": confidence,
            "warning": (
                "Chapter detection confidence is low. Review boundaries before generating lessons."
                if confidence == "low"
                else None
            ),
        }

    def _build_accepted_chapters(
        self,
        *,
        book_id: int,
        chapters: list[dict[str, Any]],
        page_numbers: set[int],
    ) -> list[dict[str, Any]]:
        if not chapters:
            raise ChapterBoundaryValidationError("At least one chapter boundary is required.")
        if not page_numbers:
            raise ChapterBoundaryValidationError("Extract pages before reviewing chapter boundaries.")

        accepted_chapters = []
        for index, chapter in enumerate(chapters, start=1):
            title = str(chapter.get("title", "")).strip()
            start_page = chapter.get("start_page")
            end_page = chapter.get("end_page")

            if not title:
                raise ChapterBoundaryValidationError("Each accepted chapter needs a title.")
            if not isinstance(start_page, int) or not isinstance(end_page, int):
                raise ChapterBoundaryValidationError("Chapter start and end pages must be numbers.")
            if start_page > end_page:
                raise ChapterBoundaryValidationError("Chapter start page must be before its end page.")
            if start_page not in page_numbers or end_page not in page_numbers:
                raise ChapterBoundaryValidationError("Chapter boundaries must use extracted PDF pages.")

            accepted_chapters.append(
                {
                    "book_id": book_id,
                    "chapter_number": int(chapter.get("chapter_number", index)),
                    "title": title,
                    "start_page": start_page,
                    "end_page": end_page,
                    "start_source_location": f"book:{book_id}:page:{start_page}",
                    "end_source_location": f"book:{book_id}:page:{end_page}",
                    "review_status": "accepted",
                }
            )

        ranges_by_start_page = sorted(
            accepted_chapters,
            key=lambda chapter: (chapter["start_page"], chapter["end_page"]),
        )
        previous_end_page = 0
        for chapter in ranges_by_start_page:
            if chapter["start_page"] <= previous_end_page:
                raise ChapterBoundaryValidationError("Accepted chapter boundaries cannot overlap.")
            previous_end_page = chapter["end_page"]

        return accepted_chapters
