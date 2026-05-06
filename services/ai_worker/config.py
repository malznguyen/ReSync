"""
Module: config
Service: ai_worker
Purpose: Build AI worker service settings from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACKER_CONFIG = Path(__file__).resolve().with_name("bytetrack.yaml")


@dataclass(frozen=True)
class AiWorkerSettings:
    camera_id: str
    redis_url: str
    yolo_model_path: str
    tracker_config_path: str
    stale_frame_seconds: float
    poll_interval_seconds: float
    fps_log_interval_seconds: float
    redis_socket_timeout_seconds: float
    yolo_confidence_threshold: float
    yolo_iou_threshold: float
    yolo_image_size: int
    yolo_device: str | None
    log_level: str

    @classmethod
    def from_env(cls) -> "AiWorkerSettings":
        load_environment()
        camera_id = os.getenv("CAMERA_ID") or os.getenv("AI_WORKER_CAMERA_ID")
        if camera_id is None or camera_id == "":
            raise RuntimeError("Missing required environment variable: CAMERA_ID")

        return cls(
            camera_id=camera_id,
            redis_url=get_redis_url(),
            yolo_model_path=os.getenv("YOLO_MODEL_PATH", "yolov8n-pose.pt"),
            tracker_config_path=os.getenv(
                "AI_WORKER_TRACKER_CONFIG_PATH",
                str(DEFAULT_TRACKER_CONFIG),
            ),
            stale_frame_seconds=_env_float("AI_WORKER_STALE_FRAME_SECONDS", 2.0),
            poll_interval_seconds=_env_float("AI_WORKER_POLL_SECONDS", 0.03),
            fps_log_interval_seconds=_env_float(
                "AI_WORKER_FPS_LOG_INTERVAL_SECONDS",
                10.0,
            ),
            redis_socket_timeout_seconds=_env_float(
                "AI_WORKER_REDIS_SOCKET_TIMEOUT_SECONDS",
                2.0,
            ),
            yolo_confidence_threshold=_env_float("AI_WORKER_YOLO_CONF", 0.25),
            yolo_iou_threshold=_env_float("AI_WORKER_YOLO_IOU", 0.7),
            yolo_image_size=_env_int("AI_WORKER_YOLO_IMGSZ", 640),
            yolo_device=_optional_env("AI_WORKER_DEVICE"),
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


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return None
    return value


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
