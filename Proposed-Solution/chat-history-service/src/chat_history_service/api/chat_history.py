"""Authenticated, owner-scoped Chat History REST API.

This isolated router uses the existing database connection factory and schema.
Replace SQL calls with your repository/service methods when their exact contracts are available.
"""
import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from psycopg.types.json import Jsonb
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from psycopg.rows import dict_row

from chat_history_service.persistence.database import database_connection_factory
from chat_history_service.security.jwt_auth import get_current_principal
from chat_history_service.security.project_access import require_project_access

router = APIRouter(prefix="/api/v1", tags=["Chat History"])
bearer = HTTPBearer(auto_error=False)


class NewConversation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="New chat", min_length=1, max_length=255)


class RenameConversation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=255)


class NewMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1)
    generate_answer: bool = False
    top_k: int = Field(default=5, ge=1, le=50)


def current_identity(
    principal: Annotated[dict, Depends(get_current_principal)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> tuple[str, str]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer access token required")
    return principal["sub"], credentials.credentials


Identity = Annotated[tuple[str, str], Depends(current_identity)]


logger = logging.getLogger(__name__)


def _call_rag_answer(project_id: UUID, question: str, top_k: int, token: str) -> dict:
    """Call the existing authenticated RAG API; never accept assistant text from clients."""
    url = os.getenv("RAG_ANSWER_URL", "http://127.0.0.1:8000/api/v1/answers")
    payload = json.dumps({
        "project_id": str(project_id), "question": question, "top_k": top_k,
    }).encode("utf-8")
    req = Request(url, data=payload, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=180) as response:
            data = json.load(response)
    except HTTPError as exc:
        logger.warning("RAG service HTTP error: %s", exc.code)
        raise HTTPException(status_code=502, detail=f"RAG service returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        logger.exception("RAG service unavailable or invalid response")
        raise HTTPException(status_code=502, detail="RAG service unavailable or returned invalid JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("answer"), str):
        raise HTTPException(status_code=502, detail="RAG response missing answer")
    if not isinstance(data.get("sources", []), list):
        raise HTTPException(status_code=502, detail="RAG response has invalid sources")
    return data


def _get_owned_conversation(conn: Any, conversation_id: UUID, owner_id: str) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT id, project_id, owner_id, title, created_at, updated_at
               FROM chat_conversations WHERE id=%s AND owner_id=%s""",
            (conversation_id, owner_id),
        )
        conversation = cur.fetchone()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _project_is_authorized(project_id: UUID, access_token: str) -> None:
    require_project_access(str(project_id), access_token)


@router.post("/projects/{project_id}/conversations", status_code=201)
def create_conversation(project_id: UUID, request: NewConversation, identity: Identity):
    owner_id, token = identity
    _project_is_authorized(project_id, token)
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be blank")
    conversation_id = uuid4()
    with database_connection_factory.get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """INSERT INTO chat_conversations (id, project_id, owner_id, title)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id, project_id, owner_id, title, created_at, updated_at""",
                (conversation_id, project_id, owner_id, title),
            )
            result = cur.fetchone()
    return result


@router.get("/projects/{project_id}/conversations")
def list_conversations(project_id: UUID, identity: Identity, limit: int = 50, offset: int = 0):
    owner_id, token = identity
    _project_is_authorized(project_id, token)
    if not (1 <= limit <= 100) or offset < 0:
        raise HTTPException(status_code=422, detail="Invalid pagination")
    with database_connection_factory.get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """SELECT id, project_id, owner_id, title, created_at, updated_at
                   FROM chat_conversations WHERE owner_id=%s AND project_id=%s
                   ORDER BY updated_at DESC, id DESC LIMIT %s OFFSET %s""",
                (owner_id, project_id, limit, offset),
            )
            return cur.fetchall()


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: UUID, identity: Identity):
    owner_id, token = identity
    with database_connection_factory.get_connection() as conn:
        conv = _get_owned_conversation(conn, conversation_id, owner_id)
    _project_is_authorized(conv["project_id"], token)
    return conv


@router.patch("/conversations/{conversation_id}")
def rename_conversation(conversation_id: UUID, request: RenameConversation, identity: Identity):
    owner_id, token = identity
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be blank")
    with database_connection_factory.get_connection() as conn:
        conv = _get_owned_conversation(conn, conversation_id, owner_id)
        _project_is_authorized(conv["project_id"], token)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """UPDATE chat_conversations SET title=%s, updated_at=now()
                   WHERE id=%s AND owner_id=%s
                   RETURNING id, project_id, owner_id, title, created_at, updated_at""",
                (title, conversation_id, owner_id),
            )
            result = cur.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID, identity: Identity):
    owner_id, token = identity
    with database_connection_factory.get_connection() as conn:
        conv = _get_owned_conversation(conn, conversation_id, owner_id)
        _project_is_authorized(conv["project_id"], token)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM chat_conversations WHERE id=%s AND owner_id=%s",
                (conversation_id, owner_id),
            )
    # chat_messages rows are removed by ON DELETE CASCADE.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: UUID, identity: Identity, limit: int = 100, offset: int = 0):
    owner_id, token = identity
    if not (1 <= limit <= 200) or offset < 0:
        raise HTTPException(status_code=422, detail="Invalid pagination")
    with database_connection_factory.get_connection() as conn:
        conv = _get_owned_conversation(conn, conversation_id, owner_id)
        _project_is_authorized(conv["project_id"], token)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """SELECT id, conversation_id, role, content, sources, status, created_at
                   FROM chat_messages WHERE conversation_id=%s
                   ORDER BY created_at ASC, id ASC LIMIT %s OFFSET %s""",
                (conversation_id, limit, offset),
            )
            return cur.fetchall()


@router.post("/conversations/{conversation_id}/messages", status_code=201)
def add_user_message(conversation_id: UUID, request: NewMessage, identity: Identity):
    """Save a user message; optionally generate and persist a trusted RAG answer.

    The default preserves the existing simple-message API contract.
    generate_answer=True returns {user_message, assistant_message, rag}.
    """
    owner_id, token = identity
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message cannot be blank")

    with database_connection_factory.get_connection() as conn:
        conv = _get_owned_conversation(conn, conversation_id, owner_id)
        _project_is_authorized(conv["project_id"], token)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """INSERT INTO chat_messages
                   (id, conversation_id, role, content, sources, status)
                   VALUES (%s, %s, 'user', %s, '[]'::jsonb, 'completed')
                   RETURNING id, conversation_id, role, content, sources, status, created_at""",
                (uuid4(), conversation_id, content),
            )
            user_message = cur.fetchone()
            cur.execute(
                "UPDATE chat_conversations SET updated_at=now() WHERE id=%s AND owner_id=%s",
                (conversation_id, owner_id),
            )

    if not request.generate_answer:
        return user_message

    # Intentionally call RAG after committing the question. If generation fails,
    # the original user question remains visible and the endpoint reports a 502.
    rag = _call_rag_answer(conv["project_id"], content, request.top_k, token)
    sources = rag.get("sources") or []

    with database_connection_factory.get_connection() as conn:
        # Re-check ownership before persisting (the conversation may have been deleted).
        checked = _get_owned_conversation(conn, conversation_id, owner_id)
        _project_is_authorized(checked["project_id"], token)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """INSERT INTO chat_messages
                   (id, conversation_id, role, content, sources, status)
                   VALUES (%s, %s, 'assistant', %s, %s, 'completed')
                   RETURNING id, conversation_id, role, content, sources, status, created_at""",
                (uuid4(), conversation_id, rag["answer"], Jsonb(sources)),
            )
            assistant_message = cur.fetchone()
            cur.execute(
                "UPDATE chat_conversations SET updated_at=now() WHERE id=%s AND owner_id=%s",
                (conversation_id, owner_id),
            )

    return {"user_message": user_message, "assistant_message": assistant_message, "rag": {
        "model": rag.get("model"),
        "duration_seconds": rag.get("duration_seconds"),
        "included_chunks": rag.get("included_chunks"),
    }}
