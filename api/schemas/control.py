"""
Module: control
Service: api
Purpose: Validate control API payloads and shape API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Polygon = list[tuple[float, float]]


def _validate_rtsp_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"rtsp", "rtsps"} or not parsed.netloc:
        raise ValueError("rtsp_url must be an rtsp:// or rtsps:// URL")
    return value


def _validate_http_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an http:// or https:// URL")
    return value


def _validate_polygon(value: Polygon) -> Polygon:
    if len(value) < 4:
        raise ValueError("polygon must include at least 3 points plus a closing point")
    if value[0] != value[-1]:
        raise ValueError("polygon must be closed by repeating the first point last")

    unique_points = {point for point in value[:-1]}
    if len(unique_points) < 3:
        raise ValueError("polygon must contain at least 3 unique points")

    for x, y in value:
        if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0:
            raise ValueError("polygon coordinates must be normalized between 0 and 1")
    return value


class Token(BaseModel):
    access_token: str = Field(..., examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = Field(default="bearer", examples=["bearer"])


class CameraCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Dining Room Camera",
                    "rtsp_url": "rtsp://mediamtx:8554/dining-room",
                    "status": "active",
                }
            ]
        }
    )

    name: str = Field(..., min_length=1, max_length=120)
    rtsp_url: str = Field(..., description="RTSP stream URL for the camera.")
    status: str = Field(default="inactive", min_length=1, max_length=40)

    @field_validator("rtsp_url")
    @classmethod
    def validate_rtsp_url(cls, value: str) -> str:
        return _validate_rtsp_url(value)


class CameraUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Dining Room Camera A",
                    "rtsp_url": "rtsp://mediamtx:8554/dining-room-a",
                    "status": "active",
                }
            ]
        }
    )

    name: str | None = Field(default=None, min_length=1, max_length=120)
    rtsp_url: str | None = Field(default=None)
    status: str | None = Field(default=None, min_length=1, max_length=40)

    @field_validator("rtsp_url")
    @classmethod
    def validate_rtsp_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_rtsp_url(value)

    @model_validator(mode="after")
    def require_update_field(self) -> "CameraUpdate":
        if self.name is None and self.rtsp_url is None and self.status is None:
            raise ValueError("at least one camera field must be provided")
        return self


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    rtsp_url: str
    status: str
    created_at: datetime


class ZoneCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "camera_id": "00000000-0000-0000-0000-000000000101",
                    "name": "Table 4",
                    "polygon": [[0.10, 0.20], [0.40, 0.20], [0.40, 0.55], [0.10, 0.20]],
                    "active": True,
                }
            ]
        }
    )

    camera_id: UUID
    name: str = Field(..., min_length=1, max_length=120)
    polygon: Polygon
    active: bool = True

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: Polygon) -> Polygon:
        return _validate_polygon(value)


class ZoneUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Table 4 Expanded",
                    "polygon": [[0.10, 0.18], [0.43, 0.18], [0.43, 0.57], [0.10, 0.18]],
                    "active": True,
                }
            ]
        }
    )

    camera_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    polygon: Polygon | None = None
    active: bool | None = None

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: Polygon | None) -> Polygon | None:
        if value is None:
            return value
        return _validate_polygon(value)

    @model_validator(mode="after")
    def require_update_field(self) -> "ZoneUpdate":
        if (
            self.camera_id is None
            and self.name is None
            and self.polygon is None
            and self.active is None
        ):
            raise ValueError("at least one zone field must be provided")
        return self


class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    camera_id: UUID
    name: str
    polygon: Polygon
    active: bool


class WebhookCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "url": "https://restaurant.example.com/webhooks/resync",
                    "secret": "replace-with-restaurant-webhook-secret",
                    "active": True,
                    "test_on_create": True,
                }
            ]
        }
    )

    url: str
    secret: str = Field(..., min_length=16)
    active: bool = True
    test_on_create: bool = False

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _validate_http_url(value)


class WebhookUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "url": "https://restaurant.example.com/webhooks/resync-v2",
                    "active": True,
                }
            ]
        }
    )

    url: str | None = None
    secret: str | None = Field(default=None, min_length=16)
    active: bool | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_http_url(value)

    @model_validator(mode="after")
    def require_update_field(self) -> "WebhookUpdate":
        if self.url is None and self.secret is None and self.active is None:
            raise ValueError("at least one webhook field must be provided")
        return self


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    active: bool
    created_at: datetime
    secret_set: bool = True


class VisitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID | None
    zone_id: UUID | None
    camera_id: UUID | None
    entered_at: datetime
    left_at: datetime | None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    customer_id: UUID | None
    zone_id: UUID | None
    camera_id: UUID | None
    track_id: str | None
    timestamp: datetime
    status: str
    payload: dict[str, Any]
    webhook_response: dict[str, Any] | None


class PaginatedVisitsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "limit": 100,
                    "offset": 0,
                    "items": [
                        {
                            "id": "10000000-0000-0000-0000-000000000001",
                            "customer_id": "20000000-0000-0000-0000-000000000001",
                            "zone_id": "30000000-0000-0000-0000-000000000001",
                            "camera_id": "00000000-0000-0000-0000-000000000101",
                            "entered_at": "2026-05-06T08:30:00Z",
                            "left_at": "2026-05-06T08:55:00Z",
                        }
                    ],
                }
            ]
        }
    )

    limit: int
    offset: int
    items: list[VisitResponse]


class PaginatedEventsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "limit": 100,
                    "offset": 0,
                    "items": [
                        {
                            "id": "40000000-0000-0000-0000-000000000001",
                            "event_type": "hand_raise",
                            "customer_id": "20000000-0000-0000-0000-000000000001",
                            "zone_id": "30000000-0000-0000-0000-000000000001",
                            "camera_id": "00000000-0000-0000-0000-000000000101",
                            "track_id": "track-42",
                            "timestamp": "2026-05-06T08:32:10Z",
                            "status": "dispatched",
                            "payload": {"zone_name": "Table 4"},
                            "webhook_response": {"status_code": 200},
                        }
                    ],
                }
            ]
        }
    )

    limit: int
    offset: int
    items: list[EventResponse]
