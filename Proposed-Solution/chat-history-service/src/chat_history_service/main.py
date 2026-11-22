from fastapi import FastAPI, HTTPException
import logging



#from chat_history_service.persistence.database import database
from chat_history_service.persistence.database import (
    database_connection_factory,
)

from chat_history_service.api.chat_history import (
    router as chat_history_router,
)

logger = logging.getLogger(__name__)
app = FastAPI(
    title="Chat History Service",
    version="1.0.0",
)
app.include_router(chat_history_router)

@app.get("/health")
def health():
    return {"status": "UP"}



@app.get("/health/db")
def database_health():
    try:
        with database_connection_factory.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        return {"status": "UP", "database": "UP"}

    except Exception:
        logger.exception("Chat History database health check failed")

        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )