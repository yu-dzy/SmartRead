from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader


class UploadedBookNotFoundError(Exception):
    pass


class PdfExtractionError(Exception):
    def __init__(self, message: str, book: dict[str, Any]) -> None:
        super().__init__(message)
        self.message = message
        self.book = book


CHAPTER_HEADING_PATTERN = re.compile(
    r"^\s*(?:chapter|ch\.?)\s+(?P<label>[0-9ivxlcdm]+)\s*[:.\-]?\s*(?P<title>.+)?$",
    re.IGNORECASE,
)
WEAK_NUMBERED_HEADING_PATTERN = re.compile(
    r"^\s*(?P<label>\d{1,2})[.)]\s+(?P<title>[A-Z][A-Za-z0-9 '&,\-]+)\s*$"
)


class UploadedBookStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
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
