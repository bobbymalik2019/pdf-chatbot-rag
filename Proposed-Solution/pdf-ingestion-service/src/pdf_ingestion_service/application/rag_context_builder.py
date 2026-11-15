#Accept retrieved document chunks in relevance order.
#Preserve document IDs, chunk IDs, filenames and page references.
#Format each chunk with a stable citation marker such as [S1].
#Stay within a configured context budget.
#Produce a structured result that the prompt builder and citation validator can consume.


import logging
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict
from pdf_ingestion_service.models.rag_context import ContextSource, RAGContext, RetrievedChunk


logger = logging.getLogger(__name__)


class RAGContextBuilder:

    def __init__(self, max_context_chars: int = 12000):
        if max_context_chars <= 0:
            raise ValueError(
                "max_context_chars must be positive"
            )

        self.max_context_chars = max_context_chars

    def build(
        self,
        chunks: list[RetrievedChunk]
    ) -> RAGContext:

        context_parts: list[str] = []
        sources: list[ContextSource] = []

        used_chars = 0
        truncated = False

        for chunk in chunks:

            content = chunk.content.strip()

            if not content:
                continue

            marker = f"S{len(sources) + 1}"

            page_label = (
                str(chunk.page_number)
                if chunk.page_number is not None
                else "Unknown"
            )

            # Format evidence as data, not as instructions.
            section = (
                f"[{marker}]\n"
                f"Document: {chunk.filename}\n"
                f"Page: {page_label}\n"
                f"Content:\n{content}\n"
            )

            separator = "\n---\n" if context_parts else ""
            required_chars = len(separator) + len(section)

            if used_chars + required_chars > self.max_context_chars:
                truncated = True
                continue

            context_parts.append(separator + section)
            used_chars += required_chars

            sources.append(
                ContextSource(
                    marker=marker,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    filename=chunk.filename,
                    page_number=chunk.page_number
                )
            )

        context_text = "".join(context_parts)

        logger.info(
            "RAG CONTEXT BUILT | "
            "input_chunks=%d | included_chunks=%d | "
            "context_chars=%d | truncated=%s",
            len(chunks),
            len(sources),
            len(context_text),
            truncated
        )

        return RAGContext(
            context_text=context_text,
            sources=sources,
            included_chunks=len(sources),
            truncated=truncated
        )
# Shared module-level instance
rag_context_builder = RAGContextBuilder()