import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from smartread_api.chapter_concepts import OpenAIConceptsTakeawaysGenerator
from smartread_api.chapter_summaries import OpenAIChapterSummaryGenerator
from smartread_api.uploaded_books import (
    AcceptedChapterNotFoundError,
    ChapterBoundaryValidationError,
    ChapterSummaryNotFoundError,
    ConceptsTakeawaysNotFoundError,
    PdfExtractionError,
    UploadedBookNotFoundError,
    UploadedBookStore,
)

PDF_READ_ERROR_MESSAGE = "The PDF could not be read. Upload a valid PDF and try again."


def create_app(
    database_path: str | Path | None = None,
    summary_generator: object | None = None,
    concepts_generator: object | None = None,
) -> FastAPI:
    app = FastAPI(title="SmartRead API")
    store = UploadedBookStore(database_path or _default_database_path())
    chapter_summary_generator = summary_generator or OpenAIChapterSummaryGenerator.from_env()
    concepts_takeaways_generator = (
        concepts_generator or OpenAIConceptsTakeawaysGenerator.from_env()
    )

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

    @app.post("/books/{book_id}/extraction")
    def extract_book_pages(book_id: int) -> dict[str, object]:
        try:
            return store.extract_pages_for_book(book_id)
        except UploadedBookNotFoundError:
            raise HTTPException(status_code=404, detail="Uploaded Book was not found.") from None
        except PdfExtractionError as error:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": error.message,
                    "retryable": True,
                    "book": error.book,
                },
            ) from None

    @app.get("/books/{book_id}/pages")
    def list_book_pages(book_id: int) -> dict[str, list[dict[str, object]]]:
        try:
            return {"pages": store.list_pages_for_book(book_id)}
        except UploadedBookNotFoundError:
            raise HTTPException(status_code=404, detail="Uploaded Book was not found.") from None

    @app.post("/books/{book_id}/chapter-detection")
    def detect_book_chapters(book_id: int) -> dict[str, object]:
        try:
            return store.detect_chapters_for_book(book_id)
        except UploadedBookNotFoundError:
            raise HTTPException(status_code=404, detail="Uploaded Book was not found.") from None

    @app.get("/books/{book_id}/chapters")
    def list_book_chapters(book_id: int) -> dict[str, list[dict[str, object]]]:
        try:
            return {"chapters": store.list_chapters_for_book(book_id)}
        except UploadedBookNotFoundError:
            raise HTTPException(status_code=404, detail="Uploaded Book was not found.") from None

    @app.put("/books/{book_id}/chapter-boundaries")
    def save_chapter_boundaries(book_id: int, payload: dict[str, object]) -> dict[str, object]:
        try:
            chapters = payload.get("chapters")
            if not isinstance(chapters, list):
                raise ChapterBoundaryValidationError("Accepted chapter boundaries are required.")
            return store.save_accepted_chapter_boundaries(book_id, chapters)
        except UploadedBookNotFoundError:
            raise HTTPException(status_code=404, detail="Uploaded Book was not found.") from None
        except ChapterBoundaryValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None

    @app.get("/books/{book_id}/chapter-boundaries")
    def list_chapter_boundaries(book_id: int) -> dict[str, list[dict[str, object]]]:
        try:
            return {"chapters": store.list_accepted_chapter_boundaries(book_id)}
        except UploadedBookNotFoundError:
            raise HTTPException(status_code=404, detail="Uploaded Book was not found.") from None

    @app.get("/books/{book_id}/chapter-boundaries/{chapter_number}/source-pages")
    def get_chapter_source_pages(book_id: int, chapter_number: int) -> dict[str, object]:
        try:
            return store.get_accepted_chapter_source_pages(book_id, chapter_number)
        except AcceptedChapterNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Accepted chapter boundary was not found.",
            ) from None

    @app.post("/books/{book_id}/chapter-boundaries/{chapter_number}/summary")
    def generate_chapter_summary(book_id: int, chapter_number: int) -> dict[str, object]:
        try:
            result = store.generate_chapter_summary(
                book_id,
                chapter_number,
                chapter_summary_generator,
            )
        except AcceptedChapterNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Accepted chapter boundary was not found.",
            ) from None

        if result["generation_status"] == "failed":
            raise HTTPException(
                status_code=422,
                detail={
                    "message": result["generation_error"],
                    "retryable": True,
                    "summary": result,
                },
            )

        return result

    @app.get("/books/{book_id}/chapter-boundaries/{chapter_number}/summary")
    def get_chapter_summary(book_id: int, chapter_number: int) -> dict[str, object]:
        try:
            return store.get_chapter_summary(book_id, chapter_number)
        except AcceptedChapterNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Accepted chapter boundary was not found.",
            ) from None
        except ChapterSummaryNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Chapter Summary has not been generated yet.",
            ) from None

    @app.get("/books/{book_id}/chapter-boundaries/{chapter_number}/summary/citations/{citation_id}/evidence")
    def get_chapter_summary_citation_evidence(
        book_id: int,
        chapter_number: int,
        citation_id: str,
    ) -> dict[str, object]:
        try:
            return store.get_chapter_summary_citation_evidence(
                book_id,
                chapter_number,
                citation_id,
            )
        except AcceptedChapterNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Accepted chapter boundary was not found.",
            ) from None
        except ChapterSummaryNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Chapter Summary has not been generated yet.",
            ) from None

    @app.post("/books/{book_id}/chapter-boundaries/{chapter_number}/concepts-takeaways")
    def generate_chapter_concepts_takeaways(
        book_id: int,
        chapter_number: int,
    ) -> dict[str, object]:
        try:
            result = store.generate_chapter_concepts_takeaways(
                book_id,
                chapter_number,
                concepts_takeaways_generator,
            )
        except AcceptedChapterNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Accepted chapter boundary was not found.",
            ) from None

        if result["generation_status"] == "failed":
            raise HTTPException(
                status_code=422,
                detail={
                    "message": result["generation_error"],
                    "retryable": True,
                    "concepts_takeaways": result,
                },
            )

        return result

    @app.get("/books/{book_id}/chapter-boundaries/{chapter_number}/concepts-takeaways")
    def get_chapter_concepts_takeaways(
        book_id: int,
        chapter_number: int,
    ) -> dict[str, object]:
        try:
            return store.get_chapter_concepts_takeaways(book_id, chapter_number)
        except AcceptedChapterNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Accepted chapter boundary was not found.",
            ) from None
        except ConceptsTakeawaysNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Core Concepts and Key Takeaways have not been generated yet.",
            ) from None

    return app


def _default_database_path() -> Path:
    return Path(os.environ.get("SMARTREAD_DB_PATH", ".smartread/smartread.db"))


def _looks_like_readable_pdf(content: bytes) -> bool:
    return content.startswith(b"%PDF-") and b"%%EOF" in content[-1024:]


app = create_app()
