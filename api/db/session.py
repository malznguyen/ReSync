"""
Module: session
Service: api
Purpose: Create SQLAlchemy engine and session factories for PostgreSQL.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from api.core.config import get_postgres_url


def create_postgres_engine() -> Engine:
    return create_engine(get_postgres_url(), pool_pre_ping=True)


engine = create_postgres_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Session:
    return SessionLocal()
