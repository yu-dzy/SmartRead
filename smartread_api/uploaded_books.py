from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


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
                        uploaded_at,
                        upload_status,
                        processing_status,
                        error_message
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        original_filename,
                        content_type,
                        file_size,
                        content_sha256,
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
