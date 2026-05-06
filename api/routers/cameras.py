"""
Module: cameras
Service: api
Purpose: Manage camera stream configuration and notify ingestion on changes.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.redis_client import NotificationError, publish_camera_reload
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
