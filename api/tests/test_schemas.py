"""
Module: test_schemas
Service: api
Purpose: Verify request validation for API control payloads.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.schemas import CameraCreate, ZoneCreate


def test_camera_create_rejects_non_rtsp_url() -> None:
    with pytest.raises(ValidationError):
        CameraCreate(
            name="Dining Room",
            rtsp_url="http://example.com/stream",
            status="active",
        )


def test_zone_create_requires_closed_polygon() -> None:
    with pytest.raises(ValidationError):
        ZoneCreate(
            camera_id="00000000-0000-0000-0000-000000000101",
            name="Table 1",
            polygon=[(0.1, 0.1), (0.4, 0.1), (0.4, 0.4)],
            active=True,
        )
