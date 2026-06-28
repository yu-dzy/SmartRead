# SmartRead

SmartRead is a private learning system for cited chapter lessons, active recall, and targeted review.

## Issue #2 PDF Upload Slice

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

The Streamlit shell accepts PDF uploads only and sends the selected file to FastAPI. FastAPI validates that the file looks like a readable PDF, persists Uploaded Book metadata in SQLite, and does not extract text yet.

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
