"""
Module: schemas
Service: ai_worker
Purpose: Define the source-of-truth Pydantic schemas for AI track output.
"""

from __future__ import annotations

import time
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

NormalizedFloat = Annotated[float, Field(ge=0.0, le=1.0)]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
BoundingBox = tuple[NormalizedFloat, NormalizedFloat, NormalizedFloat, NormalizedFloat]
KeypointTriplet = tuple[NormalizedFloat, NormalizedFloat, Confidence]
PolygonPoint = tuple[NormalizedFloat, NormalizedFloat]
TrackLifecycleState = Literal["UNKNOWN", "STANDING", "SEATED", "HAND_RAISING"]


class FrameMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frame_id: str
    timestamp: float = Field(ge=0.0)
    camera_id: str


class FrameEnvelope(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    metadata: FrameMetadata
    frame_bytes: bytes


class Track(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track_id: str
    bbox: BoundingBox
    keypoints: list[KeypointTriplet] = Field(..., min_length=17, max_length=17)
    confidence: Confidence
    customer_id: str | None = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox_extent(cls, bbox: BoundingBox) -> BoundingBox:
        x, y, width, height = bbox
        if x + width > 1.000001 or y + height > 1.000001:
            raise ValueError("bbox must stay within normalized frame bounds")
        return bbox


class TrackOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frame_id: str
    timestamp: float = Field(default_factory=time.time, ge=0.0)
    camera_id: str
    tracks: list[Track]


class TrackState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track_id: str
    camera_id: str
    current_zone_id: str | None = None
    zone_entered_at: float | None = Field(default=None, ge=0.0)
    is_seated: bool = False
    seated_at: float | None = Field(default=None, ge=0.0)
    hand_raise_started_at: float | None = Field(default=None, ge=0.0)
    last_seen_at: float = Field(default_factory=time.time, ge=0.0)
    state: TrackLifecycleState = "UNKNOWN"
    last_hand_raise_fired_at: float | None = Field(default=None, ge=0.0)


class ZoneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: str
    camera_id: str
    name: str
    polygon: list[PolygonPoint] = Field(..., min_length=3)

    def to_shapely(self) -> Any:
        from shapely.geometry import Polygon

        return Polygon(self.polygon)


class WebhookEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: Literal["hand_raise", "customer_seated"]
    camera_id: str
    zone_id: str
    zone_name: str
    track_id: str
    customer_id: str | None
    timestamp: float = Field(ge=0.0)
    payload: dict[str, Any] = Field(default_factory=dict)
