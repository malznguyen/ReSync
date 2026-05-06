"""
Module: gstreamer_pipeline
Service: ingestion
Purpose: Open RTSP streams through OpenCV's GStreamer backend when available.
"""

from __future__ import annotations

import logging
from typing import Any

import cv2


def build_gstreamer_pipeline(rtsp_url: str, latency_ms: int) -> str:
    return (
        f"rtspsrc location={rtsp_url} latency={latency_ms} protocols=tcp "
        "! rtph264depay "
        "! avdec_h264 "
        "! videoconvert "
        "! appsink emit-signals=true sync=false max-buffers=1 drop=true"
    )


def open_gstreamer_capture(
    camera_id: str,
    rtsp_url: str,
    latency_ms: int,
    logger: logging.Logger,
) -> Any | None:
    if not _opencv_has_gstreamer():
        logger.warning(
            "OpenCV build does not expose GStreamer; falling back to VideoCapture",
            extra={"camera_id": camera_id},
        )
        return None

    pipeline = build_gstreamer_pipeline(rtsp_url, latency_ms)
    try:
        capture = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    except cv2.error as exc:
        logger.warning(
            "Failed to initialize GStreamer pipeline; falling back to VideoCapture",
            extra={"camera_id": camera_id, "error": str(exc)},
        )
        return None

    if capture.isOpened():
        return capture

    capture.release()
    logger.warning(
        "GStreamer pipeline did not open; falling back to VideoCapture",
        extra={"camera_id": camera_id},
    )
    return None


def _opencv_has_gstreamer() -> bool:
    build_info = cv2.getBuildInformation()
    for line in build_info.splitlines():
        normalized = line.strip().upper()
        if normalized.startswith("GSTREAMER:"):
            return "YES" in normalized
    return False
