"""
Module: test_schemas
Service: ai_worker
Purpose: Verify the AI worker output schema enforces normalized track payloads.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from schemas import Track, TrackOutput


def test_track_output_serializes_exact_payload_shape() -> None:
    keypoints = [(0.1, 0.2, 0.9)] * 17
    output = TrackOutput(
        frame_id="frame-1",
        timestamp=123.456,
        camera_id="camera-1",
        tracks=[
            Track(
                track_id="7",
                bbox=(0.25, 0.2, 0.3, 0.4),
                keypoints=keypoints,
                confidence=0.88,
            )
        ],
    )

    payload = json.loads(output.model_dump_json())

    assert payload == {
        "frame_id": "frame-1",
        "timestamp": 123.456,
        "camera_id": "camera-1",
        "tracks": [
            {
                "track_id": "7",
                "bbox": [0.25, 0.2, 0.3, 0.4],
                "keypoints": [[0.1, 0.2, 0.9]] * 17,
                "confidence": 0.88,
                "customer_id": None,
            }
        ],
    }


def test_track_rejects_pixel_space_bbox() -> None:
    with pytest.raises(ValidationError):
        Track(
            track_id="7",
            bbox=(100.0, 50.0, 200.0, 300.0),
            keypoints=[(0.1, 0.2, 0.9)] * 17,
            confidence=0.88,
        )


def test_track_rejects_bbox_that_exits_frame() -> None:
    with pytest.raises(ValidationError):
        Track(
            track_id="7",
            bbox=(0.9, 0.1, 0.2, 0.3),
            keypoints=[(0.1, 0.2, 0.9)] * 17,
            confidence=0.88,
        )


def test_track_requires_exactly_17_keypoints() -> None:
    with pytest.raises(ValidationError):
        Track(
            track_id="7",
            bbox=(0.1, 0.1, 0.2, 0.3),
            keypoints=[(0.1, 0.2, 0.9)] * 16,
            confidence=0.88,
        )
