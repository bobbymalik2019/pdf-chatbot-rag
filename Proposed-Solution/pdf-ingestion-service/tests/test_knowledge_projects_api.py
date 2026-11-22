
import uuid

import pytest
from fastapi.testclient import TestClient

from pdf_ingestion_service.main import app
from pdf_ingestion_service.security.current_user import (
    get_current_app_user,
)


BASE_URL = "/api/v1/projects"

# Existing provisioned development user in rag_db.app_users.
DEV_USER_ID = "52105c3d-ead8-4371-a2e8-f9d009452057"


@pytest.fixture(scope="module")
def http_session():
    """
    Run API tests in-process with an authenticated
    application user.

    The override applies only to this TestClient and
    is removed when the fixture finishes.
    """

    def mock_current_app_user():
        return {
            "id": uuid.UUID(DEV_USER_ID),
            "external_user_id": "test-user",
            "display_name": "Test User",
        }

    previous_override = app.dependency_overrides.get(
        get_current_app_user
    )

    app.dependency_overrides[get_current_app_user] = (
        mock_current_app_user
    )

    try:
        with TestClient(app) as client:
            yield client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(
                get_current_app_user,
                None,
            )
        else:
            app.dependency_overrides[get_current_app_user] = (
                previous_override
            )


@pytest.fixture(scope="module")
def created_project(http_session):
    """
    Create a unique Knowledge Project for this test module.
    """

    payload = {
        "name": f"Automated_Test_{uuid.uuid4().hex}",
        "description": "Created by pytest integration tests",
        "tags": ["pytest", "integration"],
    }

    response = http_session.post(
        BASE_URL,
        json=payload,
    )

    assert response.status_code in (200, 201), response.text

    project = response.json()

    assert project["name"] == payload["name"]
    assert project["owner_id"] == DEV_USER_ID

    return project


def test_create_knowledge_project(created_project):
    """Verify successful project creation."""

    assert uuid.UUID(created_project["id"])

    assert created_project["description"] == (
        "Created by pytest integration tests"
    )

    assert created_project["tags"] == [
        "pytest",
        "integration",
    ]

    assert created_project["created_at"] is not None


def test_list_knowledge_projects(http_session, created_project):
    """Verify the new project appears in the list."""

    response = http_session.get(BASE_URL)

    assert response.status_code == 200

    projects = response.json()

    assert isinstance(projects, list)

    assert any(
        project["id"] == created_project["id"]
        for project in projects
    )

    assert all(
        project["owner_id"] == DEV_USER_ID
        for project in projects
    )


def test_get_knowledge_project_by_id(
    http_session,
    created_project,
):
    """Retrieve an existing project using its UUID."""

    project_id = created_project["id"]

    response = http_session.get(
        f"{BASE_URL}/{project_id}"
    )

    assert response.status_code == 200

    project = response.json()

    assert project["id"] == project_id
    assert project["name"] == created_project["name"]
    assert project["owner_id"] == DEV_USER_ID


def test_get_nonexistent_knowledge_project(http_session):
    """Verify HTTP 404 for a nonexistent project."""

    nonexistent_id = (
        "00000000-0000-0000-0000-000000000000"
    )

    response = http_session.get(
        f"{BASE_URL}/{nonexistent_id}"
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Knowledge Project not found"
    )


def test_create_duplicate_knowledge_project(
    http_session,
    created_project,
):
    """Verify HTTP 409 for a duplicate project name."""

    payload = {
        "name": created_project["name"],
        "description": "Duplicate project test",
        "tags": ["duplicate"],
    }

    response = http_session.post(
        BASE_URL,
        json=payload,
    )

    assert response.status_code == 409

    assert response.json()["detail"] == (
        "A project with this name already exists"
    )


def test_create_knowledge_project_invalid_tags(http_session):
    """Verify Pydantic request validation returns HTTP 422."""

    payload = {
        "name": "Invalid Project",
        "description": "Testing request validation",
        "tags": "not-an-array",
    }

    response = http_session.post(
        BASE_URL,
        json=payload,
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        error["loc"] == ["body", "tags"]
        and error["type"] == "list_type"
        for error in errors
    )
