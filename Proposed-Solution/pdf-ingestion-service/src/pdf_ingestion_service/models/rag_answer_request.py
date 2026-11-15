
from pydantic import BaseModel, Field


class RAGAnswerRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=50
    )
