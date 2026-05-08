"""
Module: system
Service: api
Purpose: Expose runtime system controls for developer debugging workflows.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.config import (
    get_mock_camera_ffmpeg_binary,
    get_mock_camera_rtsp_url,
    get_mock_camera_source_path,
    get_reid_enabled_default,
)
from api.core.redis_client import redis_connection
from api.core.security import get_current_subject
from api.core.system_control import (
    MockCameraUnavailable,
    RuntimeFlags,
    SystemControlError,
    mock_camera_manager,
)
from api.schemas import MockCameraStatus, SystemStatus, SystemToggleRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/system",
    tags=["system"],
    dependencies=[Depends(get_current_subject)],
)


@router.get(
    "/status",
    response_model=SystemStatus,
    summary="Get system control status",
    description=(
        "Return Redis-backed runtime flags and the current mock camera process state."
    ),
)
def get_system_status() -> SystemStatus:
    return _build_status()


@router.post(
    "/inference/toggle",
    response_model=SystemStatus,
    summary="Enable or pause AI inference",
    description=(
        "Write system:inference:enabled to Redis. AI workers skip frame processing "
        "while this flag is false."
    ),
)
def toggle_inference(payload: SystemToggleRequest) -> SystemStatus:
    try:
        with redis_connection() as client:
            RuntimeFlags(client).set_inference_enabled(payload.enabled)
    except SystemControlError as exc:
        logger.exception("Failed to update inference control flag")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return _build_status()


@router.post(
    "/reid/toggle",
    response_model=SystemStatus,
    summary="Enable or pause ReID matching",
    description=(
        "Write system:reid:enabled to Redis. AI workers with an initialized ReID "
        "pipeline skip customer matching while this flag is false."
    ),
)
def toggle_reid(payload: SystemToggleRequest) -> SystemStatus:
    try:
        with redis_connection() as client:
            RuntimeFlags(client).set_reid_enabled(payload.enabled)
    except SystemControlError as exc:
        logger.exception("Failed to update ReID control flag")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return _build_status()


@router.post(
    "/mock-camera/toggle",
    response_model=SystemStatus,
    summary="Start or stop the mock camera streamer",
    description=(
        "Start or stop the ffmpeg demo.mp4 loop and record the desired mock camera "
        "state in Redis."
    ),
)
def toggle_mock_camera(payload: SystemToggleRequest) -> SystemStatus:
    source_path = get_mock_camera_source_path()
    rtsp_url = get_mock_camera_rtsp_url()
    ffmpeg_binary = get_mock_camera_ffmpeg_binary()

    try:
        with redis_connection() as client:
            flags = RuntimeFlags(client)
            if payload.enabled:
                mock_camera_manager.start(source_path, rtsp_url, ffmpeg_binary)
            else:
                mock_camera_manager.stop()
            flags.set_mock_camera_enabled(payload.enabled)
    except MockCameraUnavailable as exc:
        logger.exception("Mock camera streamer is unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except SystemControlError as exc:
        logger.exception("Failed to update mock camera control flag")
        if payload.enabled:
            mock_camera_manager.stop()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return _build_status()


def _build_status() -> SystemStatus:
    try:
        with redis_connection() as client:
            flags = RuntimeFlags(client)
            inference_enabled = flags.get_inference_enabled()
            reid_enabled = flags.get_reid_enabled(get_reid_enabled_default())
            mock_camera_enabled = flags.get_mock_camera_enabled()
    except SystemControlError as exc:
        logger.exception("Failed to read system control status")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    mock_camera = mock_camera_manager.status(
        enabled=mock_camera_enabled,
        source_path=get_mock_camera_source_path(),
        rtsp_url=get_mock_camera_rtsp_url(),
        ffmpeg_binary=get_mock_camera_ffmpeg_binary(),
    )
    return SystemStatus(
        inference_enabled=inference_enabled,
        reid_enabled=reid_enabled,
        mock_camera=MockCameraStatus(**mock_camera.__dict__),
    )
