import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from smartread_api.uploaded_books import UploadedBookStore

PDF_READ_ERROR_MESSAGE = "The PDF could not be read. Upload a valid PDF and try again."


def create_app(database_path: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="SmartRead API")
    store = UploadedBookStore(database_path or _default_database_path())

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "smartread-api",
            "message": "SmartRead API is available",
        }

    @app.post("/books/uploads", status_code=201)
    async def upload_book(file: UploadFile = File(...)) -> dict[str, object]:
        filename = file.filename or ""
        content_type = file.content_type or "application/octet-stream"
        if not filename.lower().endswith(".pdf") or content_type != "application/pdf":
            raise HTTPException(
                status_code=415,
                detail="SmartRead accepts PDF uploads only.",
            )

        content = await file.read()
        if not _looks_like_readable_pdf(content):
            book = store.save_failed_pdf(
                original_filename=filename,
                content_type=content_type,
                content=content,
                error_message=PDF_READ_ERROR_MESSAGE,
            )
            raise HTTPException(
                status_code=422,
                detail={
                    "message": PDF_READ_ERROR_MESSAGE,
                    "retryable": True,
                    "book": book,
                },
            )

        return store.save_uploaded_pdf(
            original_filename=filename,
            content_type=content_type,
            content=content,
        )

    @app.get("/books")
    def list_books() -> dict[str, list[dict[str, object]]]:
        return {"books": store.list_uploaded_books()}

    return app


def _default_database_path() -> Path:
    return Path(os.environ.get("SMARTREAD_DB_PATH", ".smartread/smartread.db"))


def _looks_like_readable_pdf(content: bytes) -> bool:
    return content.startswith(b"%PDF-") and b"%%EOF" in content[-1024:]


app = create_app()
