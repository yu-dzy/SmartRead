from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class UploadResult:
    success: bool
    message: str
    book: dict[str, Any] | None = None
    retryable: bool = False


@dataclass(frozen=True)
class BookListResult:
    success: bool
    books: list[dict[str, Any]]
    message: str = ""


@dataclass(frozen=True)
class ExtractionResult:
    success: bool
    message: str
    summary: dict[str, int]
    book: dict[str, Any] | None = None
    pages: list[dict[str, Any]] | None = None
    retryable: bool = False


def get_uploaded_books(
    api_base_url: str,
    *,
    client: httpx.Client | None = None,
) -> BookListResult:
    http_client = client or httpx.Client(timeout=5.0)
    try:
        response = http_client.get(f"{api_base_url.rstrip('/')}/books")
        response.raise_for_status()
        return BookListResult(success=True, books=response.json()["books"])
    except httpx.HTTPError:
        return BookListResult(
            success=False,
            books=[],
            message="Uploaded books could not be loaded. Refresh after FastAPI is available.",
        )


def extract_pdf_text_from_api(
    api_base_url: str,
    *,
    book_id: int,
    client: httpx.Client | None = None,
) -> ExtractionResult:
    http_client = client or httpx.Client(timeout=20.0)
    try:
        response = http_client.post(f"{api_base_url.rstrip('/')}/books/{book_id}/extraction")
        if response.status_code == 200:
            payload = response.json()
            summary = payload["summary"]
            return ExtractionResult(
                success=True,
                message=_format_extraction_summary(summary),
                summary=summary,
                book=payload["book"],
                pages=payload["pages"],
            )

        detail = response.json().get("detail", {})
        if isinstance(detail, dict):
            return ExtractionResult(
                success=False,
                message=detail.get("message", "Extraction failed. Retry with this PDF."),
                summary={},
                book=detail.get("book"),
                retryable=bool(detail.get("retryable", True)),
            )
        if isinstance(detail, str):
            return ExtractionResult(success=False, message=detail, summary={}, retryable=True)

        return ExtractionResult(
            success=False,
            message="Extraction failed. Retry with this PDF.",
            summary={},
            retryable=True,
        )
    except httpx.HTTPError:
        return ExtractionResult(
            success=False,
            message="Extraction failed. Check the FastAPI backend, then try again.",
            summary={},
            retryable=True,
        )


def upload_pdf_to_api(
    api_base_url: str,
    *,
    filename: str,
    content: bytes,
    content_type: str,
    client: httpx.Client | None = None,
) -> UploadResult:
    http_client = client or httpx.Client(timeout=10.0)
    try:
        response = http_client.post(
            f"{api_base_url.rstrip('/')}/books/uploads",
            files={"file": (filename, content, content_type)},
        )
        if response.status_code == 201:
            book = response.json()
            return UploadResult(
                success=True,
                message=f"{book['original_filename']} is ready in SmartRead.",
                book=book,
            )

        detail = response.json().get("detail", {})
        if isinstance(detail, dict):
            return UploadResult(
                success=False,
                message=detail.get("message", "Upload failed. Choose a PDF you own and try again."),
                retryable=bool(detail.get("retryable", True)),
                book=detail.get("book"),
            )
        if isinstance(detail, str):
            return UploadResult(success=False, message=detail, retryable=True)

        return UploadResult(
            success=False,
            message="Upload failed. Choose a PDF you own and try again.",
            retryable=True,
        )
    except httpx.HTTPError:
        return UploadResult(
            success=False,
            message="Upload failed. Check the FastAPI backend, then try again.",
            retryable=True,
        )


def _format_extraction_summary(summary: dict[str, int]) -> str:
    return (
        "Extraction complete: "
        f"{summary['page_count']} pages, "
        f"{summary['text_page_count']} with text, "
        f"{summary['blank_page_count']} blank."
    )
