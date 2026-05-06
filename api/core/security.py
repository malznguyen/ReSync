"""
Module: security
Service: api
Purpose: Issue and validate HS256 JWT bearer tokens for API access.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from api.core.config import (
    get_api_admin_password_hash,
    get_api_admin_username,
    get_jwt_algorithm,
    get_jwt_expire_minutes,
    get_jwt_secret,
)

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_context.verify(plain_password, password_hash)


def authenticate_admin(username: str, password: str) -> str | None:
    try:
        expected_username = get_api_admin_username()
        password_hash = get_api_admin_password_hash()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if username != expected_username:
        return None
    if not verify_password(password, password_hash):
        return None
    return username


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=get_jwt_expire_minutes(),
    )
    claims = {"sub": subject, "exp": expires_at}
    return jwt.encode(claims, get_jwt_secret(), algorithm=get_jwt_algorithm())


def get_current_subject(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[get_jwt_algorithm()],
        )
    except (JWTError, RuntimeError) as exc:
        raise credentials_error from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or subject == "":
        raise credentials_error
    return subject
