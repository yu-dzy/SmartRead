from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class ApiStatus:
    connected: bool
    heading: str
    detail: str


def get_api_status(api_base_url: str, client: httpx.Client | None = None) -> ApiStatus:
    http_client = client or httpx.Client(timeout=2.0)
    try:
        response = http_client.get(f"{api_base_url.rstrip('/')}/health")
        response.raise_for_status()
        payload = response.json()
        return ApiStatus(
            connected=True,
            heading="FastAPI connected",
            detail=payload["message"],
        )
    except httpx.HTTPError:
        return ApiStatus(
            connected=False,
            heading="FastAPI unavailable",
            detail="Start the FastAPI backend, then refresh this Streamlit page.",
        )
