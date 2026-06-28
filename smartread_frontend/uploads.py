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
