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
PLACEHOLDER_PREFIXES = ("CHANGE_ME", "GENERATE_WITH")


def load_environment() -> None:
    """Load local environment files without overriding shell-provided values."""
    load_dotenv(REPO_ROOT / ".env", override=False)
    load_dotenv(REPO_ROOT / ".env.example", override=False)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def require_real_env(name: str) -> str:
    value = require_env(name)
    if value == "password" or value.startswith(PLACEHOLDER_PREFIXES):
        raise RuntimeError(f"Environment variable {name} must be set to a real value")
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


def get_jwt_secret() -> str:
    load_environment()
    secret = require_real_env("JWT_SECRET")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters")
    return secret


def get_jwt_algorithm() -> str:
    load_environment()
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    if algorithm != "HS256":
        raise RuntimeError("JWT_ALGORITHM must be HS256")
    return algorithm


def get_jwt_expire_minutes() -> int:
    load_environment()
    raw_value = os.getenv("JWT_EXPIRE_MINUTES", "1440")
    expire_minutes = int(raw_value)
    if expire_minutes <= 0:
        raise RuntimeError("JWT_EXPIRE_MINUTES must be greater than zero")
    return expire_minutes


def get_api_admin_username() -> str:
    load_environment()
    return os.getenv("API_ADMIN_USERNAME", "admin")


def get_api_admin_password_hash() -> str:
    load_environment()
    return require_real_env("API_ADMIN_PASSWORD_HASH").replace("$$", "$")
