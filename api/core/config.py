"""
Module: config
Service: api
Purpose: Build service connection settings from environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_environment() -> None:
    """Load local environment files without overriding shell-provided values."""
    load_dotenv(REPO_ROOT / ".env", override=False)
    load_dotenv(REPO_ROOT / ".env.example", override=False)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_postgres_url(driver: str = "postgresql+psycopg") -> str:
    load_environment()
    user = quote_plus(require_env("POSTGRES_USER"))
    password = quote_plus(require_env("POSTGRES_PASSWORD"))
    host = require_env("POSTGRES_HOST")
    port = require_env("POSTGRES_PORT")
    database = require_env("POSTGRES_DB")
    return f"{driver}://{user}:{password}@{host}:{port}/{database}"


def get_redis_url() -> str:
    load_environment()
    password = os.getenv("REDIS_PASSWORD", "")
    host = require_env("REDIS_HOST")
    port = require_env("REDIS_PORT")
    auth = f":{quote_plus(password)}@" if password else ""
    return f"redis://{auth}{host}:{port}/0"


def get_rabbitmq_url() -> str:
    load_environment()
    user = quote_plus(require_env("RABBITMQ_USER"))
    password = quote_plus(require_env("RABBITMQ_PASSWORD"))
    host = require_env("RABBITMQ_HOST")
    port = require_env("RABBITMQ_PORT")
    return f"amqp://{user}:{password}@{host}:{port}/%2F"
