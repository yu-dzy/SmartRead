from fastapi import FastAPI

app = FastAPI(title="SmartRead API")


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "smartread-api",
        "message": "SmartRead API is available",
    }
