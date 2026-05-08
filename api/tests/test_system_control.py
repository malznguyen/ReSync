"""
Module: test_system_control
Service: api
Purpose: Verify Redis-backed runtime controls and mock camera availability checks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from api.core.system_control import MockCameraProcessManager, RuntimeFlags


def test_runtime_flags_default_to_live_processing() -> None:
    flags = RuntimeFlags(FakeRedis({}))

    assert flags.get_inference_enabled()
    assert flags.get_reid_enabled(default=True)
    assert not flags.get_mock_camera_enabled()


def test_runtime_flags_write_bool_strings() -> None:
    redis = FakeRedis({})
    flags = RuntimeFlags(redis)

    flags.set_inference_enabled(False)
    flags.set_reid_enabled(True)
    flags.set_mock_camera_enabled(True)

    assert redis.values == {
        "system:inference:enabled": "false",
        "system:reid:enabled": "true",
        "system:mock_camera:enabled": "true",
    }


def test_runtime_flags_use_default_for_invalid_values() -> None:
    flags = RuntimeFlags(FakeRedis({"system:inference:enabled": "not-a-bool"}))

    assert flags.get_inference_enabled()


def test_mock_camera_status_reports_missing_source() -> None:
    manager = MockCameraProcessManager()
    missing_path = Path("missing-demo.mp4")

    status = manager.status(
        enabled=True,
        source_path=missing_path,
        rtsp_url="rtsp://mediamtx:8554/test",
        ffmpeg_binary="ffmpeg",
    )

    assert not status.available
    assert not status.running
    assert status.detail == f"Mock camera source not found: {missing_path}"


class FakeRedis:
    def __init__(self, values: dict[str, Any]) -> None:
        self.values = values

    def get(self, key: str) -> Any | None:
        return self.values.get(key)

    def set(self, key: str, value: str) -> bool:
        self.values[key] = value
        return True
