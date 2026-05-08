"""
Module: schemas
Service: api
Purpose: Export Pydantic schemas for request and response bodies.
"""

from api.schemas.control import (
    CameraCreate,
    CameraResponse,
    CameraUpdate,
    EventResponse,
    MockCameraStatus,
    PaginatedEventsResponse,
    PaginatedVisitsResponse,
    SystemStatus,
    SystemToggleRequest,
    Token,
    VisitResponse,
    WebhookCreate,
    WebhookResponse,
    WebhookUpdate,
    ZoneCreate,
    ZoneResponse,
    ZoneUpdate,
)

__all__ = [
    "CameraCreate",
    "CameraResponse",
    "CameraUpdate",
    "EventResponse",
    "MockCameraStatus",
    "PaginatedEventsResponse",
    "PaginatedVisitsResponse",
    "SystemStatus",
    "SystemToggleRequest",
    "Token",
    "VisitResponse",
    "WebhookCreate",
    "WebhookResponse",
    "WebhookUpdate",
    "ZoneCreate",
    "ZoneResponse",
    "ZoneUpdate",
]
