
from fastapi import Depends, HTTPException, status

from pdf_ingestion_service.security.jwt_auth import (
    get_current_principal,
)
from pdf_ingestion_service.dependencies import (
    app_user_repository,
)


def get_current_app_user(
    principal: dict = Depends(get_current_principal),
) -> dict:
    """
    Resolve a validated Charter26 SSO identity
    to an existing Chatbot application user.
    """

    external_user_id = principal["sub"]

    user = app_user_repository.find_by_external_user_id(
        external_user_id=external_user_id
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not provisioned for the Chatbot application",
        )

    return user
