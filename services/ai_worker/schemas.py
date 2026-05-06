"""
Module: schemas
Service: ai_worker
Purpose: Define the source-of-truth Pydantic schemas for AI track output.
"""

from __future__ import annotations

import time
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

NormalizedFloat = Annotated[float, Field(ge=0.0, le=1.0)]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
BoundingBox = tuple[NormalizedFloat, NormalizedFloat, NormalizedFloat, NormalizedFloat]
KeypointTriplet = tuple[NormalizedFloat, NormalizedFloat, Confidence]


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
