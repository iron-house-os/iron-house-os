from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_placeholder_routes_are_registered() -> None:
    routes = [
        "/api/v1/projects",
        "/api/v1/suppliers",
        "/api/v1/rfqs",
        "/api/v1/bids",
        "/api/v1/documents",
        "/api/v1/equipment",
        "/api/v1/users",
        "/api/v1/auth",
    ]

    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
