"""Authorize Knowledge Project access through the RAG service.

Pass the original validated access token; never trust project ownership from the client.
"""
import httpx
from fastapi import HTTPException, status

from chat_history_service.config.settings import settings


def require_project_access(project_id: str, token: str) -> None:
    # Use a service-to-service address, not a browser-facing URL.
    base_url = settings.rag_api_base_url.rstrip("/")
    url = f"{base_url}/api/v1/projects/{project_id}"
    try:
        with httpx.Client(timeout=5.0, follow_redirects=False) as client:
            response = client.get(url, headers={"Authorization": f"Bearer {token}"})
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="Knowledge Project authorization unavailable") from exc

    if response.status_code in (401, 403):
        # Do not disclose existence of another user's project.
        raise HTTPException(status_code=404, detail="Knowledge Project not found")
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Knowledge Project not found")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Knowledge Project authorization unavailable")

    # The project endpoint is assumed to already enforce owner access.
    # Do not treat an unprotected RAG endpoint as an authorization oracle.
    try:
        payload = response.json()
        returned_id = payload.get("id")
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=503, detail="Invalid Knowledge Project authorization response") from exc
    if str(returned_id) != str(project_id):
        raise HTTPException(status_code=503, detail="Inconsistent Knowledge Project response")
