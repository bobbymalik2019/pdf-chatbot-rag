from fastapi import FastAPI
from pdf_ingestion_service.api.routes import router
from pdf_ingestion_service.api.ingestion import router as ingestion_router
from pdf_ingestion_service.config.logging_config import (
    configure_logging
)
from pdf_ingestion_service.api.rag_answer import (
    router as rag_answer_router
)

from pdf_ingestion_service.api.knowledge_projects import (
    router as projects_router
)
from pdf_ingestion_service.api.document_files import (
    router as document_files_router,
)
from fastapi import Depends

configure_logging(level="INFO")

app = FastAPI(
    title="PDF Ingestion Service",
    description="Document ingestion for RAG-based chatbot",
    version="0.1.0"
)

from pdf_ingestion_service.security.jwt_auth import (
    get_current_principal,
)

app.include_router(router)
app.include_router(ingestion_router)
app.include_router(projects_router)
app.include_router(rag_answer_router)
app.include_router(document_files_router)


@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/api/v1/auth/verify", tags=["Authentication"])
def verify_authentication(
    principal: dict = Depends(get_current_principal),
):
    return {
        "authenticated": True,
        "subject": principal["sub"],
        "issuer": principal["iss"],
        "audience": principal["aud"],
        "client_id": principal["client_id"],
    }
