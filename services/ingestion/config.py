"""
Module: config
Service: ingestion
Purpose: Build ingestion service settings from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class IngestionSettings:
    postgres_url: str
    redis_url: str
    expected_fps: float
    fps_warning_threshold: float
    drop_warning_rate: float
    fps_log_interval_seconds: float
    camera_refresh_seconds: float
    watchdog_poll_seconds: float
    watchdog_initial_backoff_seconds: float
    watchdog_max_backoff_seconds: float
    watchdog_stable_seconds: float
    stream_read_failure_seconds: float
    redis_socket_timeout_seconds: float
    jpeg_quality: int
    gstreamer_enabled: bool
    gstreamer_latency_ms: int
    log_level: str

    @classmethod
    def from_env(cls) -> "IngestionSettings":
        load_environment()
        return cls(
            postgres_url=get_postgres_url(),
            redis_url=get_redis_url(),
            expected_fps=_env_float("INGESTION_EXPECTED_FPS", 30.0),
            fps_warning_threshold=_env_float("INGESTION_FPS_WARNING_THRESHOLD", 25.0),
            drop_warning_rate=_env_float("INGESTION_DROP_WARNING_RATE", 0.05),
            fps_log_interval_seconds=_env_float(
                "INGESTION_FPS_LOG_INTERVAL_SECONDS", 10.0
            ),
            camera_refresh_seconds=_env_float("INGESTION_CAMERA_REFRESH_SECONDS", 30.0),
            watchdog_poll_seconds=_env_float("INGESTION_WATCHDOG_POLL_SECONDS", 1.0),
            watchdog_initial_backoff_seconds=_env_float(
                "INGESTION_WATCHDOG_INITIAL_BACKOFF_SECONDS",
                1.0,
            ),
            watchdog_max_backoff_seconds=_env_float(
                "INGESTION_WATCHDOG_MAX_BACKOFF_SECONDS",
                5.0,
            ),
            watchdog_stable_seconds=_env_float(
                "INGESTION_WATCHDOG_STABLE_SECONDS", 30.0
            ),
            stream_read_failure_seconds=_env_float(
                "INGESTION_STREAM_READ_FAILURE_SECONDS",
                5.0,
            ),
            redis_socket_timeout_seconds=_env_float(
                "INGESTION_REDIS_SOCKET_TIMEOUT_SECONDS",
                2.0,
            ),
            jpeg_quality=_env_int("INGESTION_JPEG_QUALITY", 85),
            gstreamer_enabled=_env_bool("INGESTION_GSTREAMER_ENABLED", True),
            gstreamer_latency_ms=_env_int("INGESTION_GSTREAMER_LATENCY_MS", 100),
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


def get_postgres_url() -> str:
    user = quote_plus(require_env("POSTGRES_USER"))
    password = quote_plus(require_env("POSTGRES_PASSWORD"))
    host = require_env("POSTGRES_HOST")
    port = require_env("POSTGRES_PORT")
    database = require_env("POSTGRES_DB")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def get_redis_url() -> str:
    password = os.getenv("REDIS_PASSWORD", "")
    host = require_env("REDIS_HOST")
    port = require_env("REDIS_PORT")
    auth = f":{quote_plus(password)}@" if password else ""
    return f"redis://{auth}{host}:{port}/0"


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


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}
