"""
Module: analytics
Service: api
Purpose: Expose paginated read APIs for visits and behavioral events.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.security import get_current_subject
from api.db.session import get_session
from api.models import AnalyticsEvent, Visit
from api.schemas import PaginatedEventsResponse, PaginatedVisitsResponse

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_subject)],
)


@router.get(
    "/visits",
    response_model=PaginatedVisitsResponse,
    summary="List visits",
    description=(
        "Return analytics visits with date range and zone filters. Results are "
        "always paginated with limit and offset."
    ),
)
def list_visits(
    session: Annotated[Session, Depends(get_session)],
    start_at: datetime | None = Query(
        default=None, description="Inclusive entered_at start."
    ),
    end_at: datetime | None = Query(
        default=None, description="Inclusive entered_at end."
    ),
    zone_id: UUID | None = Query(default=None, description="Filter by zone ID."),
    limit: Annotated[int, Query(ge=1, le=500, examples=[100])] = 100,
    offset: Annotated[int, Query(ge=0, examples=[0])] = 0,
) -> PaginatedVisitsResponse:
    statement = select(Visit).order_by(Visit.entered_at.desc(), Visit.id.desc())
    if start_at is not None:
        statement = statement.where(Visit.entered_at >= start_at)
    if end_at is not None:
        statement = statement.where(Visit.entered_at <= end_at)
    if zone_id is not None:
        statement = statement.where(Visit.zone_id == zone_id)

    rows = session.scalars(statement.limit(limit).offset(offset)).all()
    return PaginatedVisitsResponse(limit=limit, offset=offset, items=list(rows))


@router.get(
    "/events",
    response_model=PaginatedEventsResponse,
    summary="List events",
    description=(
        "Return behavioral events with date range, zone, and event_type filters. "
        "Results are always paginated with limit and offset."
    ),
)
def list_events(
    session: Annotated[Session, Depends(get_session)],
    start_at: datetime | None = Query(
        default=None, description="Inclusive timestamp start."
    ),
    end_at: datetime | None = Query(
        default=None, description="Inclusive timestamp end."
    ),
    zone_id: UUID | None = Query(default=None, description="Filter by zone ID."),
    event_type: str | None = Query(default=None, description="Filter by event type."),
    limit: Annotated[int, Query(ge=1, le=500, examples=[100])] = 100,
    offset: Annotated[int, Query(ge=0, examples=[0])] = 0,
) -> PaginatedEventsResponse:
    statement = select(AnalyticsEvent).order_by(
        AnalyticsEvent.timestamp.desc(),
        AnalyticsEvent.id.desc(),
    )
    if start_at is not None:
        statement = statement.where(AnalyticsEvent.timestamp >= start_at)
    if end_at is not None:
        statement = statement.where(AnalyticsEvent.timestamp <= end_at)
    if zone_id is not None:
        statement = statement.where(AnalyticsEvent.zone_id == zone_id)
    if event_type is not None:
        statement = statement.where(AnalyticsEvent.event_type == event_type)

    rows = session.scalars(statement.limit(limit).offset(offset)).all()
    return PaginatedEventsResponse(limit=limit, offset=offset, items=list(rows))
