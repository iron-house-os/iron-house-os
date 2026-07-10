from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.services.request_context import get_request_audit_context

app = FastAPI()


@app.get("/context")
def context(request: Request) -> dict[str, str | None]:
    audit_context = get_request_audit_context(request)
    return {"actor": audit_context.actor, "request_id": audit_context.request_id}


client = TestClient(app)


def test_request_context_uses_forwarded_headers() -> None:
    response = client.get(
        "/context",
        headers={"x-ihos-actor": "jeremie", "x-request-id": "req-fixed"},
    )

    assert response.status_code == 200
    assert response.json() == {"actor": "jeremie", "request_id": "req-fixed"}


def test_request_context_generates_request_id() -> None:
    response = client.get("/context")

    assert response.status_code == 200
    assert response.json()["actor"] is None
    assert response.json()["request_id"].startswith("req-")
