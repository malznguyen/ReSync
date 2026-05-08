"""
Module: test_worker
Service: ai_worker
Purpose: Verify worker frame freshness decisions before inference runs.
"""

from __future__ import annotations

from redis_io import RedisSystemControls
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


def test_system_controls_default_inference_to_enabled() -> None:
    controls = RedisSystemControls(FakeRedis({}))

    assert controls.is_inference_enabled()


def test_system_controls_read_inference_flag() -> None:
    controls = RedisSystemControls(FakeRedis({"system:inference:enabled": b"false"}))

    assert not controls.is_inference_enabled()


def test_system_controls_fallback_to_default_for_invalid_flag() -> None:
    controls = RedisSystemControls(FakeRedis({"system:reid:enabled": b"unexpected"}))

    assert controls.is_reid_enabled(default=True)


def test_system_controls_default_reid_from_settings() -> None:
    controls = RedisSystemControls(FakeRedis({}))

    assert not controls.is_reid_enabled(default=False)


class FakeRedis:
    def __init__(self, values: dict[str, bytes]) -> None:
        self.values = values

    def get(self, key: str) -> bytes | None:
        return self.values.get(key)
