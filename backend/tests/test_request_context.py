from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.services.request_context import get_request_audit_context
from app.services.auth import AuthenticatedUser

app = FastAPI()


@app.get("/context")
def context(request: Request) -> dict[str, str | None]:
    audit_context = get_request_audit_context(request)
    return {"actor": audit_context.actor, "request_id": audit_context.request_id}


@app.get("/authenticated-context")
def authenticated_context(request: Request) -> dict[str, str | None]:
    from uuid import UUID

    request.state.authenticated_user = AuthenticatedUser(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="jeremie@ironhousecivil.com",
        display_name="Jeremie Peters",
        role="admin",
        session_version=1,
    )
    audit_context = get_request_audit_context(request)
    return {"actor": audit_context.actor, "request_id": audit_context.request_id}


client = TestClient(app)


def test_request_context_uses_authenticated_identity() -> None:
    response = client.get(
        "/authenticated-context",
        headers={"x-ihos-actor": "spoofed", "x-request-id": "req-fixed"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "actor": "jeremie@ironhousecivil.com",
        "request_id": "req-fixed",
    }


def test_request_context_generates_request_id() -> None:
    response = client.get("/context")

    assert response.status_code == 200
    assert response.json()["actor"] is None
    assert response.json()["request_id"].startswith("req-")
