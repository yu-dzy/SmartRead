import httpx

from smartread_frontend.health import get_api_status


def test_get_api_status_reports_connected_when_fastapi_health_succeeds():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "status": "ok",
                "service": "smartread-api",
                "message": "SmartRead API is available",
            },
        )
    )
    client = httpx.Client(transport=transport)

    status = get_api_status("http://api.test", client=client)

    assert status.connected is True
    assert status.heading == "FastAPI connected"
    assert status.detail == "SmartRead API is available"


def test_get_api_status_reports_recoverable_error_when_fastapi_is_unavailable():
    def fail_request(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = httpx.Client(transport=httpx.MockTransport(fail_request))

    status = get_api_status("http://api.test", client=client)

    assert status.connected is False
    assert status.heading == "FastAPI unavailable"
    assert "Start the FastAPI backend" in status.detail
