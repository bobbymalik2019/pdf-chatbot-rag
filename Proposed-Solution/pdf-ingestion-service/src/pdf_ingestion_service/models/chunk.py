
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    start_page: int = Field(ge=1)
    end_page: int = Field(ge=1)
