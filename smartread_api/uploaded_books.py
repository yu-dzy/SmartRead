from __future__ import annotations

import hashlib
import sqlite3
from io import BytesIO
from datetime import UTC, datetime
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
        }

    def _to_source_page(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "book_id": row["book_id"],
            "page_number": row["page_number"],
            "source_location": row["source_location"],
            "extracted_text": row["extracted_text"],
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
