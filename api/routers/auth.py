"""
Module: auth
Service: api
Purpose: Provide JWT token issuance for the control API.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.core.security import authenticate_admin, create_access_token
from api.schemas import Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/token",
    response_model=Token,
    summary="Issue an access token",
    description=(
        "Authenticate the configured API admin account and return an HS256 JWT. "
        "Submit credentials as OAuth2 password form fields."
    ),
)
def issue_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    subject = authenticate_admin(form_data.username, form_data.password)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(subject))
