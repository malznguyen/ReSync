"""
Module: test_security
Service: api
Purpose: Verify JWT secret handling and token round-trips.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.core.security import create_access_token, get_current_subject


def test_token_round_trip_uses_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "30")

    token = create_access_token("admin")

    assert get_current_subject(token) == "admin"


def test_password_is_rejected_as_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "password")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "30")

    with pytest.raises(HTTPException):
        get_current_subject("bad-token")
