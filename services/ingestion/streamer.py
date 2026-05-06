"""
Module: streamer
Service: ingestion
Purpose: Run the per-camera RTSP decode loop and publish latest frames to Redis.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from config import IngestionSettings
from db import CameraConfig
from fps_monitor import SlidingWindowFpsMonitor
from gstreamer_pipeline import open_gstreamer_capture
from logging_config import configure_logging
from opencv_fallback import open_opencv_capture
from redis_writer import RedisFrameWriter, create_redis_client

logger = logging.getLogger(__name__)


class StreamReadError(RuntimeError):
    """Raised when a camera stream stops yielding frames."""


def camera_process_entrypoint(
    camera: CameraConfig,
    settings: IngestionSettings,
    stop_event: Any,
) -> None:
    configure_logging(settings.log_level)
    try:
        run_camera_stream(camera, settings, stop_event)
    except Exception:
        logger.exception(
            "Camera ingestion process crashed",
            extra={"camera_id": camera.camera_id, "camera_name": camera.name},
        )
        raise


def run_camera_stream(
    camera: CameraConfig,
    settings: IngestionSettings,
    stop_event: Any,
) -> None:
    redis_client = create_redis_client(
        settings.redis_url,
        settings.redis_socket_timeout_seconds,
    )
    writer = RedisFrameWriter(redis_client, settings.jpeg_quality)
    capture = None
    backend_name = "unopened"
    sequence = 0

    try:
        capture, backend_name = _open_capture(camera, settings)
        monitor = SlidingWindowFpsMonitor(
            expected_fps=settings.expected_fps,
            fps_warning_threshold=settings.fps_warning_threshold,
            drop_warning_rate=settings.drop_warning_rate,
            log_interval_seconds=settings.fps_log_interval_seconds,
            logger=logger,
        )
        logger.info(
            "Started camera ingestion loop",
            extra={
                "camera_id": camera.camera_id,
                "camera_name": camera.name,
                "backend": backend_name,
            },
        )

        read_failure_started_at: float | None = None
        while not stop_event.is_set():
            success, frame = capture.read()
            now_monotonic = time.monotonic()
            now_epoch = time.time()

            if not success or frame is None:
                read_failure_started_at = read_failure_started_at or now_monotonic
                elapsed = now_monotonic - read_failure_started_at
                if elapsed >= settings.stream_read_failure_seconds:
                    raise StreamReadError(
                        f"Camera {camera.camera_id} produced no frames for {elapsed:.2f}s"
                    )
                time.sleep(0.05)
                continue

            read_failure_started_at = None
            sequence += 1
            frame_id = _build_frame_id(camera.camera_id, now_epoch, sequence)
            writer.write_frame(
                camera_id=camera.camera_id,
                frame_id=frame_id,
                timestamp=now_epoch,
                frame=frame,
            )
            monitor.record_frame(now_monotonic)
            monitor.log_if_due(camera.camera_id, now_monotonic)

        logger.info(
            "Stopped camera ingestion loop",
            extra={"camera_id": camera.camera_id, "backend": backend_name},
        )
    finally:
        if capture is not None:
            capture.release()
        redis_client.close()


def _open_capture(
    camera: CameraConfig,
    settings: IngestionSettings,
) -> tuple[Any, str]:
    if settings.gstreamer_enabled:
        capture = open_gstreamer_capture(
            camera_id=camera.camera_id,
            rtsp_url=camera.rtsp_url,
            latency_ms=settings.gstreamer_latency_ms,
            logger=logger,
        )
        if capture is not None:
            logger.info(
                "Opened RTSP stream with GStreamer pipeline",
                extra={"camera_id": camera.camera_id},
            )
            return capture, "gstreamer"

    capture = open_opencv_capture(camera.camera_id, camera.rtsp_url, logger)
    return capture, "opencv"


def _build_frame_id(camera_id: str, timestamp: float, sequence: int) -> str:
    timestamp_ms = int(timestamp * 1000)
    return f"{camera_id}-{timestamp_ms}-{sequence}"
