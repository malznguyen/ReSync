"""
Module: opencv_fallback
Service: ingestion
Purpose: Open RTSP streams with standard cv2.VideoCapture when GStreamer is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any

import cv2


def open_opencv_capture(camera_id: str, rtsp_url: str, logger: logging.Logger) -> Any:
    capture = cv2.VideoCapture(rtsp_url)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if capture.isOpened():
        logger.info(
            "Opened RTSP stream with OpenCV VideoCapture",
            extra={"camera_id": camera_id},
        )
        return capture

    capture.release()
    raise RuntimeError(f"Failed to open RTSP stream for camera {camera_id}")
