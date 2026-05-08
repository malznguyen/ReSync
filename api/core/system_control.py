"""
Module: system_control
Service: api
Purpose: Manage Redis runtime flags and the local mock camera subprocess.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

from redis import Redis
from redis.exceptions import RedisError

SYSTEM_INFERENCE_ENABLED_KEY = "system:inference:enabled"
SYSTEM_REID_ENABLED_KEY = "system:reid:enabled"
SYSTEM_MOCK_CAMERA_ENABLED_KEY = "system:mock_camera:enabled"

logger = logging.getLogger(__name__)


class SystemControlError(RuntimeError):
    pass


class MockCameraUnavailable(SystemControlError):
    pass


@dataclass(frozen=True)
class MockCameraRuntimeStatus:
    enabled: bool
    running: bool
    available: bool
    source_path: str
    rtsp_url: str
    detail: str | None = None


class RuntimeFlags:
    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def get_inference_enabled(self) -> bool:
        return self._get_bool(SYSTEM_INFERENCE_ENABLED_KEY, default=True)

    def set_inference_enabled(self, enabled: bool) -> None:
        self._set_bool(SYSTEM_INFERENCE_ENABLED_KEY, enabled)

    def get_reid_enabled(self, default: bool) -> bool:
        return self._get_bool(SYSTEM_REID_ENABLED_KEY, default=default)

    def set_reid_enabled(self, enabled: bool) -> None:
        self._set_bool(SYSTEM_REID_ENABLED_KEY, enabled)

    def get_mock_camera_enabled(self) -> bool:
        return self._get_bool(SYSTEM_MOCK_CAMERA_ENABLED_KEY, default=False)

    def set_mock_camera_enabled(self, enabled: bool) -> None:
        self._set_bool(SYSTEM_MOCK_CAMERA_ENABLED_KEY, enabled)

    def _get_bool(self, key: str, default: bool) -> bool:
        try:
            value = self._redis.get(key)
        except RedisError as exc:
            raise SystemControlError(f"Failed to read Redis flag: {key}") from exc
        return parse_bool(value, default=default)

    def _set_bool(self, key: str, enabled: bool) -> None:
        try:
            self._redis.set(key, serialize_bool(enabled))
        except RedisError as exc:
            raise SystemControlError(f"Failed to write Redis flag: {key}") from exc


class MockCameraProcessManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None

    def status(
        self,
        enabled: bool,
        source_path: Path,
        rtsp_url: str,
        ffmpeg_binary: str,
    ) -> MockCameraRuntimeStatus:
        running = self.is_running()
        available, detail = self._availability(source_path, ffmpeg_binary)
        if enabled and not running and detail is None:
            detail = "Mock camera is enabled but the ffmpeg process is not running"

        return MockCameraRuntimeStatus(
            enabled=enabled,
            running=running,
            available=available,
            source_path=str(source_path),
            rtsp_url=rtsp_url,
            detail=detail,
        )

    def start(
        self,
        source_path: Path,
        rtsp_url: str,
        ffmpeg_binary: str,
    ) -> None:
        with self._lock:
            if self._is_running_locked():
                return

            available, detail = self._availability(source_path, ffmpeg_binary)
            if not available:
                raise MockCameraUnavailable(detail or "Mock camera is unavailable")

            command = [
                ffmpeg_binary,
                "-re",
                "-stream_loop",
                "-1",
                "-i",
                str(source_path),
                "-c",
                "copy",
                "-f",
                "rtsp",
                rtsp_url,
            ]
            try:
                self._process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError as exc:
                raise MockCameraUnavailable(f"Failed to start ffmpeg: {exc}") from exc

            logger.info(
                "Started mock camera streamer",
                extra={"source_path": str(source_path), "rtsp_url": rtsp_url},
            )

    def stop(self) -> None:
        with self._lock:
            process = self._process
            self._process = None

        if process is None:
            return
        if process.poll() is not None:
            return

        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

        logger.info("Stopped mock camera streamer")

    def is_running(self) -> bool:
        with self._lock:
            return self._is_running_locked()

    def _is_running_locked(self) -> bool:
        if self._process is None:
            return False
        if self._process.poll() is not None:
            self._process = None
            return False
        return True

    def _availability(
        self,
        source_path: Path,
        ffmpeg_binary: str,
    ) -> tuple[bool, str | None]:
        if not source_path.exists():
            return False, f"Mock camera source not found: {source_path}"
        if shutil.which(ffmpeg_binary) is None:
            return False, f"ffmpeg binary not found: {ffmpeg_binary}"
        return True, None


mock_camera_manager = MockCameraProcessManager()


def parse_bool(value: bytes | str | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def serialize_bool(enabled: bool) -> str:
    return "true" if enabled else "false"
