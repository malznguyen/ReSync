"""
Module: test_worker
Service: ai_worker
Purpose: Verify worker frame freshness decisions before inference runs.
"""

from __future__ import annotations

from schemas import FrameMetadata
from worker import is_stale_frame


def test_is_stale_frame_returns_true_after_threshold() -> None:
    metadata = FrameMetadata(
        frame_id="frame-1",
        timestamp=100.0,
        camera_id="camera-1",
    )

    assert is_stale_frame(metadata, now=102.001, stale_after_seconds=2.0)


def test_is_stale_frame_returns_false_within_threshold() -> None:
    metadata = FrameMetadata(
        frame_id="frame-1",
        timestamp=100.0,
        camera_id="camera-1",
    )

    assert not is_stale_frame(metadata, now=101.999, stale_after_seconds=2.0)
