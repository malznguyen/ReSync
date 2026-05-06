"""
Module: zones
Service: api
Purpose: Manage zone polygons and notify analytics on map changes.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.redis_client import NotificationError, publish_zone_config_updated
from api.core.security import get_current_subject
from api.db.session import get_session
from api.models import Camera, Zone
from api.schemas import ZoneCreate, ZoneResponse, ZoneUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/zones",
    tags=["zones"],
    dependencies=[Depends(get_current_subject)],
)


@router.get(
    "",
    response_model=list[ZoneResponse],
    summary="List zones",
    description="Return zone polygons, optionally filtered by camera or active state.",
)
def list_zones(
    session: Annotated[Session, Depends(get_session)],
    camera_id: UUID | None = Query(default=None, description="Filter zones by camera."),
    active: bool | None = Query(
        default=None, description="Filter zones by active flag."
    ),
    limit: Annotated[int, Query(ge=1, le=500, examples=[100])] = 100,
    offset: Annotated[int, Query(ge=0, examples=[0])] = 0,
) -> list[Zone]:
    statement = select(Zone).order_by(Zone.name.asc(), Zone.id.asc())
    if camera_id is not None:
        statement = statement.where(Zone.camera_id == camera_id)
    if active is not None:
        statement = statement.where(Zone.active.is_(active))
    statement = statement.limit(limit).offset(offset)
    return list(session.scalars(statement).all())


@router.post(
    "",
    response_model=ZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a zone",
    description=(
        "Create a closed normalized polygon for a camera and publish "
        "zone:config:updated after saving."
    ),
)
def create_zone(
    payload: ZoneCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Zone:
    _require_camera(session, payload.camera_id)
    zone = Zone(
        camera_id=payload.camera_id,
        name=payload.name,
        polygon=_polygon_to_json(payload.polygon),
        active=payload.active,
    )
    session.add(zone)
    session.commit()
    session.refresh(zone)
    _publish_zone_change("created", zone.id, zone.camera_id)
    return zone


@router.put(
    "/{zone_id}",
    response_model=ZoneResponse,
    summary="Update a zone",
    description=(
        "Update a zone polygon or metadata and invalidate zone:config:cache "
        "through Redis Pub/Sub so analytics reloads the map."
    ),
)
def update_zone(
    zone_id: UUID,
    payload: ZoneUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> Zone:
    zone = session.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found"
        )

    update_values = payload.model_dump(exclude_unset=True)
    if "camera_id" in update_values:
        _require_camera(session, update_values["camera_id"])
    if "polygon" in update_values:
        update_values["polygon"] = _polygon_to_json(update_values["polygon"])

    for field, value in update_values.items():
        setattr(zone, field, value)

    session.commit()
    session.refresh(zone)
    _publish_zone_change("updated", zone.id, zone.camera_id)
    return zone


def _require_camera(session: Session, camera_id: UUID) -> None:
    if session.get(Camera, camera_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found"
        )


def _polygon_to_json(polygon: list[tuple[float, float]]) -> list[list[float]]:
    return [[x, y] for x, y in polygon]


def _publish_zone_change(action: str, zone_id: UUID, camera_id: UUID) -> None:
    try:
        publish_zone_config_updated(
            action=action,
            zone_id=str(zone_id),
            camera_id=str(camera_id),
        )
    except NotificationError as exc:
        logger.exception("Failed to publish zone config notification")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
