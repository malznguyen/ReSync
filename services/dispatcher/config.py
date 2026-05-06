"""
Module: config
Service: dispatcher
Purpose: Build dispatcher service settings from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DispatcherSettings:
    postgres_url: str
    rabbitmq_host: str
    rabbitmq_port: int
    rabbitmq_user: str
    rabbitmq_password: str
    rabbitmq_vhost: str
    events_exchange_name: str
    dispatch_queue_name: str
    dispatch_routing_key: str
    dlq_exchange_name: str
    dlq_queue_name: str
    dlq_routing_key: str
    http_timeout_seconds: float
    max_retries: int
    retry_backoff_seconds: tuple[float, ...]
    log_level: str

    @classmethod
    def from_env(cls) -> "DispatcherSettings":
        load_environment()
        max_retries = _env_int("DISPATCHER_MAX_RETRIES", 3, minimum=0)
        retry_backoff_seconds = _env_float_tuple(
            "DISPATCHER_RETRY_BACKOFF_SECONDS",
            (1.0, 2.0, 4.0),
        )
        if len(retry_backoff_seconds) < max_retries:
            raise RuntimeError(
                "DISPATCHER_RETRY_BACKOFF_SECONDS must contain at least "
                "DISPATCHER_MAX_RETRIES values"
            )

        return cls(
            postgres_url=get_async_postgres_url(),
            rabbitmq_host=require_env("RABBITMQ_HOST"),
            rabbitmq_port=_env_int("RABBITMQ_PORT", 5672),
            rabbitmq_user=require_env("RABBITMQ_USER"),
            rabbitmq_password=require_env("RABBITMQ_PASSWORD"),
            rabbitmq_vhost=os.getenv("RABBITMQ_VHOST", "/"),
            events_exchange_name=os.getenv("RABBITMQ_EVENTS_EXCHANGE", "events"),
            dispatch_queue_name=os.getenv(
                "DISPATCHER_QUEUE_NAME",
                "webhook_dispatch",
            ),
            dispatch_routing_key=os.getenv("DISPATCHER_ROUTING_KEY", "events.#"),
            dlq_exchange_name=os.getenv("DISPATCHER_DLQ_EXCHANGE", "events.dlx"),
            dlq_queue_name=os.getenv("DISPATCHER_DLQ_QUEUE_NAME", "dlq.webhook"),
            dlq_routing_key=os.getenv(
                "DISPATCHER_DLQ_ROUTING_KEY",
                "dlq.webhook",
            ),
            http_timeout_seconds=_env_float("DISPATCHER_HTTP_TIMEOUT_SECONDS", 5.0),
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def load_environment() -> None:
    """Load local env files without overriding explicit process env values."""

    load_dotenv(REPO_ROOT / ".env", override=False)
    load_dotenv(REPO_ROOT / ".env.example", override=False)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_async_postgres_url() -> str:
    user = quote_plus(require_env("POSTGRES_USER"))
    password = quote_plus(require_env("POSTGRES_PASSWORD"))
    host = require_env("POSTGRES_HOST")
    port = require_env("POSTGRES_PORT")
    database = require_env("POSTGRES_DB")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    value = float(raw_value)
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0")
    return value


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    value = int(raw_value)
    if value < minimum:
        raise RuntimeError(f"{name} must be greater than or equal to {minimum}")
    return value


def _env_float_tuple(name: str, default: tuple[float, ...]) -> tuple[float, ...]:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default

    values = tuple(float(part.strip()) for part in raw_value.split(",") if part.strip())
    if not values:
        raise RuntimeError(f"{name} must contain at least one value")
    if any(value <= 0 for value in values):
        raise RuntimeError(f"{name} values must be greater than 0")
    return values
