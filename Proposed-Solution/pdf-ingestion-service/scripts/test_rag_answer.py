
from uuid import UUID

from pdf_ingestion_service.services.rag_answer_service import (
    rag_answer_service
)


def main():

    project_id = UUID(
        "dff9959f-0416-4006-b5e6-a9e167502671"
    )
    print(f"Searching Knowledge Project: {project_id}")
    owner_id = UUID(
        "52105c3d-ead8-4371-a2e8-f9d009452057"
    )
    #"Which patent did Bobby file?"
    result = rag_answer_service.answer(
        project_id=project_id,
        owner_id=owner_id,
        question="Which engineering college did Bobby attend",
        top_k=5
    )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
