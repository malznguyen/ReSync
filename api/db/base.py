"""
Module: base
Service: api
Purpose: Provide SQLAlchemy metadata for migrations and future ORM models.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
