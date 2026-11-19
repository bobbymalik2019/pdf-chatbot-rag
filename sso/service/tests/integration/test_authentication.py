
from fastapi.testclient import TestClient

from sso_service.main import app


client = TestClient(app)


def test_unauthenticated_user_cannot_access_profile():
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_csrf_endpoint_returns_token():
    response = client.get("/api/v1/auth/csrf")

    assert response.status_code == 200

    body = response.json()
    assert "csrf_token" in body
    assert body["csrf_token"]

    assert "sso_csrf" in response.cookies
