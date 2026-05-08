"""
Module: cameras
Service: api
Purpose: Manage camera stream configuration and notify ingestion on changes.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.config import get_redis_url
from api.core.redis_client import (
    NotificationError,
    publish_camera_reload,
    redis_connection,
)
from api.core.security import get_current_subject
from api.db.session import get_session
from api.models import Camera
from api.schemas import CameraCreate, CameraResponse, CameraUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cameras",
    tags=["cameras"],
    dependencies=[Depends(get_current_subject)],
)


@router.get(
    "",
    response_model=list[CameraResponse],
    summary="List cameras",
    description="Return configured camera streams ordered by creation time.",
)
def list_cameras(
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=500, examples=[100])] = 100,
    offset: Annotated[int, Query(ge=0, examples=[0])] = 0,
) -> list[Camera]:
    statement = (
        select(Camera).order_by(Camera.created_at.desc()).limit(limit).offset(offset)
    )
    return list(session.scalars(statement).all())


@router.get(
    "/{camera_id}/tracks/latest",
    summary="Get latest camera tracks",
    description=(
        "Return the latest AI worker TrackOutput JSON from Redis for a camera. "
        "If the AI worker has not produced tracks yet, an empty track list is returned."
    ),
)
def get_latest_tracks(
    camera_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    camera = session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    key = f"cam:{camera_id}:tracks:latest"
    try:
        with redis_connection() as client:
            payload = client.get(key)
    except RedisError as exc:
        logger.exception("Failed to read latest camera tracks")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Track output unavailable",
        ) from exc

    if payload is None:
        return {
            "frame_id": "",
            "timestamp": None,
            "camera_id": str(camera_id),
            "tracks": [],
        }

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        logger.exception("Invalid track output JSON in Redis")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid track output",
        ) from exc

    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid track output",
        )

    return parsed


@router.get(
    "/{camera_id}/overlay/stream",
    summary="Stream backend-composited camera overlay",
    description=(
        "Return an MJPEG stream where each frame is rendered by the AI worker "
        "after detection, tracking, and ReID. This guarantees monitoring overlay "
        "alignment because the boxes and keypoints are burned into the exact frame "
        "that produced cam:{camera_id}:tracks:latest."
    ),
)
def stream_overlay(
    camera_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> StreamingResponse:
    camera = session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    return StreamingResponse(
        _overlay_stream(str(camera_id)),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.post(
    "",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a camera",
    description=(
        "Create a camera stream configuration. The RTSP URL is validated and "
        "a Redis config:reload message is published after the database write."
    ),
)
def create_camera(
    payload: CameraCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Camera:
    camera = Camera(
        name=payload.name,
        rtsp_url=payload.rtsp_url,
        status=payload.status,
    )
    session.add(camera)
    session.commit()
    session.refresh(camera)
    _publish_camera_change("created", camera.id)
    return camera


@router.put(
    "/{camera_id}",
    response_model=CameraResponse,
    summary="Update a camera",
    description=(
        "Update a camera stream configuration and publish Redis config:reload "
        "so ingestion restarts affected streams."
    ),
)
def update_camera(
    camera_id: UUID,
    payload: CameraUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> Camera:
    camera = session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found"
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)

    session.commit()
    session.refresh(camera)
    _publish_camera_change("updated", camera.id)
    return camera


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a camera",
    description=(
        "Delete a camera configuration and publish Redis config:reload so "
        "ingestion stops or restarts affected streams."
    ),
)
def delete_camera(
    camera_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    camera = session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found"
        )

    session.delete(camera)
    session.commit()
    _publish_camera_change("deleted", camera_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _publish_camera_change(action: str, camera_id: UUID) -> None:
    try:
        publish_camera_reload(action=action, camera_id=str(camera_id))
    except NotificationError as exc:
        logger.exception("Failed to publish camera reload notification")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


def _overlay_stream(camera_id: str):
    client = Redis.from_url(
        get_redis_url(),
        decode_responses=False,
        socket_timeout=2,
        health_check_interval=30,
    )
    last_frame_id: str | None = None

    try:
        while True:
            try:
                with client.pipeline(transaction=False) as pipe:
                    pipe.get(f"cam:{camera_id}:overlay:latest")
                    pipe.hgetall(f"cam:{camera_id}:overlay:meta")
                    frame_bytes, raw_metadata = pipe.execute()
            except RedisError:
                logger.exception(
                    "Failed to read latest overlay frame from Redis",
                    extra={"camera_id": camera_id},
                )
                time.sleep(0.1)
                continue

            if frame_bytes is None or not raw_metadata:
                time.sleep(0.05)
                continue

            frame_id = _decode_overlay_meta(raw_metadata).get("frame_id")
            if frame_id is None or frame_id == last_frame_id:
                time.sleep(0.05)
                continue

            last_frame_id = frame_id
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                + f"Content-Length: {len(frame_bytes)}\r\n\r\n".encode("utf-8")
                + frame_bytes
                + b"\r\n"
            )
    finally:
        client.close()


def _decode_overlay_meta(raw_metadata: dict[bytes, bytes]) -> dict[str, str]:
    return {
        key.decode("utf-8"): value.decode("utf-8")
        for key, value in raw_metadata.items()
    }
