"""
Module: camera_manager
Service: ingestion
Purpose: Supervise one ingestion subprocess per active camera.
"""

from __future__ import annotations

import logging
import multiprocessing
import threading
import time
from dataclasses import dataclass
from typing import Any

from config import IngestionSettings
from db import CameraConfig, CameraRepository
from streamer import camera_process_entrypoint

logger = logging.getLogger(__name__)


@dataclass
class ManagedCamera:
    camera: CameraConfig
    stop_event: Any
    process: multiprocessing.Process | None = None
    backoff_seconds: float = 1.0
    next_start_at: float = 0.0
    last_started_at: float | None = None


class CameraWatchdog(threading.Thread):
    """Watch active camera processes and restart failed streams with backoff."""

    def __init__(
        self,
        repository: CameraRepository,
        settings: IngestionSettings,
        shutdown_event: threading.Event,
    ) -> None:
        super().__init__(name="camera-watchdog", daemon=False)
        self._repository = repository
        self._settings = settings
        self._shutdown_event = shutdown_event
        self._managed: dict[str, ManagedCamera] = {}

    def run(self) -> None:
        logger.info("Started ingestion watchdog")
        next_refresh_at = 0.0
        try:
            while not self._shutdown_event.is_set():
                now = time.monotonic()
                if now >= next_refresh_at:
                    self._refresh_active_cameras(now)
                    next_refresh_at = now + self._settings.camera_refresh_seconds

                self._monitor_processes(now)
                self._shutdown_event.wait(self._settings.watchdog_poll_seconds)
        finally:
            self._stop_all()
            self._repository.close()
            logger.info("Stopped ingestion watchdog")

    def _refresh_active_cameras(self, now: float) -> None:
        try:
            cameras = self._repository.list_active_cameras()
        except Exception:
            logger.exception("Failed to refresh active cameras from PostgreSQL")
            return

        logger.info(
            "Refreshed active camera list",
            extra={"active_camera_count": len(cameras)},
        )
        self._sync_active_cameras(cameras, now)

    def _sync_active_cameras(self, cameras: list[CameraConfig], now: float) -> None:
        active_by_id = {camera.camera_id: camera for camera in cameras}

        for camera_id in list(self._managed):
            if camera_id not in active_by_id:
                self._stop_camera(camera_id, "camera_not_active")

        for camera in cameras:
            managed = self._managed.get(camera.camera_id)
            if managed is None:
                self._managed[camera.camera_id] = ManagedCamera(
                    camera=camera,
                    stop_event=multiprocessing.Event(),
                    backoff_seconds=self._settings.watchdog_initial_backoff_seconds,
                    next_start_at=now,
                )
                continue

            if (
                managed.camera.rtsp_url != camera.rtsp_url
                or managed.camera.name != camera.name
            ):
                logger.info(
                    "Camera configuration changed; restarting ingestion process",
                    extra={"camera_id": camera.camera_id},
                )
                self._request_stop(managed, "camera_config_changed")
                managed.camera = camera
                managed.stop_event = multiprocessing.Event()
                managed.process = None
                managed.backoff_seconds = (
                    self._settings.watchdog_initial_backoff_seconds
                )
                managed.next_start_at = now

    def _monitor_processes(self, now: float) -> None:
        for managed in list(self._managed.values()):
            process = managed.process
            if process is not None and process.is_alive():
                self._reset_backoff_after_stable_run(managed, now)
                continue

            if process is not None:
                exitcode = process.exitcode
                process.join(timeout=1.0)
                managed.process = None
                if managed.stop_event.is_set():
                    continue
                self._schedule_restart(managed, now, exitcode)

            if (
                managed.process is None
                and not managed.stop_event.is_set()
                and now >= managed.next_start_at
            ):
                self._start_camera(managed, now)

    def _start_camera(self, managed: ManagedCamera, now: float) -> None:
        if managed.stop_event.is_set():
            managed.stop_event = multiprocessing.Event()

        process = multiprocessing.Process(
            target=camera_process_entrypoint,
            args=(managed.camera, self._settings, managed.stop_event),
            name=f"ingestion-{managed.camera.camera_id[:8]}",
        )
        process.start()
        managed.process = process
        managed.last_started_at = now
        logger.info(
            "Started camera ingestion process",
            extra={
                "camera_id": managed.camera.camera_id,
                "camera_name": managed.camera.name,
                "pid": process.pid,
            },
        )

    def _schedule_restart(
        self,
        managed: ManagedCamera,
        now: float,
        exitcode: int | None,
    ) -> None:
        restart_delay = managed.backoff_seconds
        managed.next_start_at = now + restart_delay
        managed.backoff_seconds = min(
            managed.backoff_seconds * 2,
            self._settings.watchdog_max_backoff_seconds,
        )
        logger.warning(
            "Camera ingestion process exited; scheduled reconnect",
            extra={
                "camera_id": managed.camera.camera_id,
                "exitcode": exitcode,
                "next_attempt_in_seconds": restart_delay,
                "next_backoff_seconds": managed.backoff_seconds,
            },
        )

    def _reset_backoff_after_stable_run(
        self, managed: ManagedCamera, now: float
    ) -> None:
        if managed.last_started_at is None:
            return
        if now - managed.last_started_at < self._settings.watchdog_stable_seconds:
            return
        managed.backoff_seconds = self._settings.watchdog_initial_backoff_seconds

    def _stop_camera(self, camera_id: str, reason: str) -> None:
        managed = self._managed.pop(camera_id)
        self._request_stop(managed, reason)

    def _request_stop(self, managed: ManagedCamera, reason: str) -> None:
        process = managed.process
        managed.stop_event.set()
        if process is None:
            return

        logger.info(
            "Stopping camera ingestion process",
            extra={"camera_id": managed.camera.camera_id, "reason": reason},
        )
        process.join(timeout=10.0)
        if process.is_alive():
            logger.warning(
                "Terminating unresponsive camera ingestion process",
                extra={"camera_id": managed.camera.camera_id, "reason": reason},
            )
            process.terminate()
            process.join(timeout=5.0)

    def _stop_all(self) -> None:
        for camera_id in list(self._managed):
            self._stop_camera(camera_id, "service_shutdown")
