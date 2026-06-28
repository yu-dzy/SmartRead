# SmartRead

SmartRead is a private learning system for cited chapter lessons, active recall, and targeted review.

## Issue #10 Quiz Feedback Slice

Start the FastAPI backend:

```powershell
C:\Users\douzh\.local\bin\uv.exe run uvicorn smartread_api.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, start the Streamlit frontend:

```powershell
$env:SMARTREAD_API_URL = "http://127.0.0.1:8000"
C:\Users\douzh\.local\bin\uv.exe run streamlit run smartread_frontend/app.py --server.address 127.0.0.1 --server.port 8502
```

Open `http://127.0.0.1:8502`.

If the backend is not running, the Streamlit app shows a recoverable FastAPI unavailable state.

The Streamlit shell accepts PDF uploads only and sends the selected file to FastAPI. FastAPI validates that the file looks like a readable PDF, persists Uploaded Book metadata in SQLite, and stores the private PDF content for extraction.

After upload, use **Extract text** on an Uploaded Book. FastAPI extracts text page by page, stores each page with its page number and source location, and returns an extraction summary. Blank pages are preserved as page records with empty text so page numbering stays stable.

After extraction, use **Detect chapters**. FastAPI detects provisional chapters from PDF outline entries first, then heading patterns in the extracted page text. Detected Chapters are stored with titles, start and end page boundaries, source locations, confidence, and detection source. Streamlit shows the provisional Book Map, low-confidence warnings, and a clear empty state when no chapters are detected.

After detection, review the Book Map in Streamlit. You can rename chapters, adjust start/end pages, merge the first two adjacent sections, split the first section when it spans more than one page, and save accepted boundaries. FastAPI validates ranges, rejects overlaps, persists accepted chapter boundaries, and exposes accepted source pages for downstream lesson generation.

After boundaries are accepted, use the Summary tab to generate one cited Summary for one selected chapter. FastAPI sends only the accepted chapter pages to the configured generator, validates structured output, rejects citations outside the accepted chapter, rejects invented source excerpts, persists the generated Summary and generation status, and shows retryable failures in Streamlit.

Persisted Summary citations render as clickable controls. Clicking a citation asks FastAPI to resolve that persisted citation ID, then updates the Study Console Evidence panel with the verified source location, page number, and focused source excerpt. Missing, stale, or invalid citations show an unverified evidence state instead of exposing full page text or crashing. Retryable evidence loading errors provide a retry action for the same citation.

Use the Core Concepts tab to generate cited Core Concepts and grounded Key Takeaways for the same accepted chapter pages. FastAPI validates the structured Pydantic output, rejects invalid citations, duplicate or generic concepts, unsupported claims, and malformed model responses, then persists generation status, content, citations, and errors. Persisted Concepts and Takeaways reload after restart and their citation controls update the same focused Evidence panel.

Use the Quiz tab to generate exactly five grounded quiz questions for the selected accepted chapter. FastAPI uses only the accepted chapter pages and generated Core Concepts, validates structured Pydantic output, rejects malformed quiz output, invalid citations, duplicate questions, ambiguous answers, unsupported questions, and trivia-only prompts, then persists generation status, questions, citations, and errors. Persisted quizzes reload after restart and citation controls resolve focused evidence excerpts.

After a quiz is generated, answer each objective question in the Quiz tab. FastAPI grades the submitted answer deterministically in application code, persists the submitted answer, returns immediate correct/incorrect feedback, and includes the correct answer, explanation, tested Core Concept, citation, source page, and source excerpt. Saved quiz progress reloads after restart and updates the Study Console Mastery panel.

Real Summary, Core Concepts, Key Takeaways, and Quiz generation use OpenAI by default with model `gpt-5.5`. Set the API key before starting FastAPI:

```powershell
$env:OPENAI_API_KEY = "your-api-key"
```

To override the default model:

```powershell
$env:SMARTREAD_OPENAI_MODEL = "gpt-5.5"
```

Missed concepts and review queues are not implemented yet.

By default, metadata is saved at `.smartread/smartread.db`. To use another database file:

```powershell
$env:SMARTREAD_DB_PATH = "C:\tmp\smartread.db"
```

## Development Checks

Run tests:

```powershell
C:\Users\douzh\.local\bin\uv.exe run pytest
```

Run linting:

```powershell
C:\Users\douzh\.local\bin\uv.exe run ruff check .
```
