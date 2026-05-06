"""
Module: config
Service: analytics
Purpose: Build analytics service settings from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AnalyticsSettings:
    camera_id: str
    redis_url: str
    postgres_dsn: str
    rabbitmq_host: str
    rabbitmq_port: int
    rabbitmq_user: str
    rabbitmq_password: str
    poll_interval_seconds: float
    redis_socket_timeout_seconds: float
    zone_cache_refresh_seconds: float
    seated_threshold_seconds: float
    hand_raise_threshold_seconds: float
    hand_raise_cooldown_seconds: float
    track_missing_seconds: float
    cleanup_interval_seconds: float
    log_level: str

    @classmethod
    def from_env(cls) -> "AnalyticsSettings":
        load_environment()
        camera_id = os.getenv("CAMERA_ID") or os.getenv("ANALYTICS_CAMERA_ID")
        if camera_id is None or camera_id == "":
            raise RuntimeError("Missing required environment variable: CAMERA_ID")

        return cls(
            camera_id=camera_id,
            redis_url=get_redis_url(),
            postgres_dsn=get_postgres_dsn(),
            rabbitmq_host=require_env("RABBITMQ_HOST"),
            rabbitmq_port=_env_int("RABBITMQ_PORT", 5672),
            rabbitmq_user=require_env("RABBITMQ_USER"),
            rabbitmq_password=require_env("RABBITMQ_PASSWORD"),
            poll_interval_seconds=_env_float("ANALYTICS_POLL_SECONDS", 0.1),
            redis_socket_timeout_seconds=_env_float(
                "ANALYTICS_REDIS_SOCKET_TIMEOUT_SECONDS",
                2.0,
            ),
            zone_cache_refresh_seconds=_env_float("ZONE_CACHE_REFRESH_SECONDS", 60.0),
            seated_threshold_seconds=_env_float("SEATED_THRESHOLD_SECONDS", 3.0),
            hand_raise_threshold_seconds=_env_float(
                "HAND_RAISE_THRESHOLD_SECONDS",
                1.5,
            ),
            hand_raise_cooldown_seconds=_env_float(
                "HAND_RAISE_COOLDOWN_SECONDS",
                10.0,
            ),
            track_missing_seconds=_env_float("ANALYTICS_TRACK_MISSING_SECONDS", 5.0),
            cleanup_interval_seconds=_env_float(
                "ANALYTICS_CLEANUP_INTERVAL_SECONDS",
                1.0,
            ),
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


def get_redis_url() -> str:
    password = os.getenv("REDIS_PASSWORD", "")
    host = require_env("REDIS_HOST")
    port = require_env("REDIS_PORT")
    auth = f":{quote_plus(password)}@" if password else ""
    return f"redis://{auth}{host}:{port}/0"


def get_postgres_dsn() -> str:
    user = quote_plus(require_env("POSTGRES_USER"))
    password = quote_plus(require_env("POSTGRES_PASSWORD"))
    host = require_env("POSTGRES_HOST")
    port = require_env("POSTGRES_PORT")
    database = require_env("POSTGRES_DB")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    value = float(raw_value)
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0")
    return value


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    value = int(raw_value)
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0")
    return value
