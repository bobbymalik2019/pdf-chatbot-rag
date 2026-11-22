
from uuid import uuid4

from pdf_ingestion_service.application.rag_context_builder import (
    RetrievedChunk,
    rag_context_builder
)
from pdf_ingestion_service.application.rag_prompt_builder import (
    rag_prompt_builder
)
from pdf_ingestion_service.llm.ollama_llm_client import (
    ollama_llm_client
)


chunks = [
    RetrievedChunk(
        chunk_id = 1,
        document_id=uuid4(),
        filename="Bobby_Malik-CV.pdf",
        content=(
            "Patents & Innovations\n"
            "US Patent Holder: Method and System for "
            "Analyzing Rolling Element Bearing Systems "
            "- US 2009/0306955 A1\n"
            "Patent Filed: Utility Patent "
            "(Docket No. H0017060)"
        )
    )
]

context = rag_context_builder.build(chunks)

prompt = rag_prompt_builder.build(
    question="Which patent did Bobby file?",
    context=context
)

response = ollama_llm_client.generate(prompt)

print("\nGENERATED ANSWER:")
print(response.answer)

print("\nMODEL:", response.model)
print("PROMPT TOKENS:", response.prompt_tokens)
print("GENERATED TOKENS:", response.generated_tokens)
print("DURATION:", response.duration_seconds)
