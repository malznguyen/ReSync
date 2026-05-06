"""
Module: engine
Service: analytics
Purpose: Connect Redis track input to zone, state, and RabbitMQ event output.
"""

from __future__ import annotations

import logging
import threading
import time

from services.ai_worker.schemas import TrackOutput
from services.analytics.config import AnalyticsSettings
from services.analytics.event_publisher import RabbitMQEventPublisher
from services.analytics.redis_io import RedisTrackReader, RedisTrackStateStore
from services.analytics.state_machine import TrackStateMachine
from services.analytics.zone_cache import ZoneConfigCache

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Run Phase 5 analytics for a single camera."""

    def __init__(
        self,
        settings: AnalyticsSettings,
        reader: RedisTrackReader,
        state_store: RedisTrackStateStore,
        zone_cache: ZoneConfigCache,
        state_machine: TrackStateMachine,
        publisher: RabbitMQEventPublisher,
    ) -> None:
        self._settings = settings
        self._reader = reader
        self._state_store = state_store
        self._zone_cache = zone_cache
        self._state_machine = state_machine
        self._publisher = publisher

    def run(self, shutdown_event: threading.Event) -> None:
        self._zone_cache.refresh()
        cache_threads = self._zone_cache.start_background_refresh(shutdown_event)
        last_processed_frame_id: str | None = None
        last_cleanup_at = 0.0

        logger.info(
            "Started analytics engine",
            extra={"camera_id": self._settings.camera_id},
        )
        try:
            while not shutdown_event.is_set():
                now_monotonic = time.monotonic()
                if (
                    now_monotonic - last_cleanup_at
                    >= self._settings.cleanup_interval_seconds
                ):
                    self._cleanup_missing_tracks()
                    last_cleanup_at = now_monotonic

                output = self._reader.read_latest(self._settings.camera_id)
                if output is None or output.frame_id == last_processed_frame_id:
                    shutdown_event.wait(self._settings.poll_interval_seconds)
                    continue

                self._process_output(output)
                last_processed_frame_id = output.frame_id
        finally:
            shutdown_event.set()
            for thread in cache_threads:
                thread.join(timeout=2.0)
            self._publisher.close()
            logger.info(
                "Stopped analytics engine",
                extra={"camera_id": self._settings.camera_id},
            )

    def _process_output(self, output: TrackOutput) -> None:
        mapper = self._zone_cache.get_mapper(self._settings.camera_id)
        for track in output.tracks:
            zone_match = mapper.match_track(track) if mapper is not None else None
            transition = self._state_machine.evaluate(output, track, zone_match)
            for event in transition.events:
                self._publisher.publish(event)
            self._state_store.set(transition.state)

    def _cleanup_missing_tracks(self) -> None:
        deleted = self._state_store.cleanup_missing_tracks(
            camera_id=self._settings.camera_id,
            now=time.time(),
            missing_after_seconds=self._settings.track_missing_seconds,
        )
        if deleted > 0:
            logger.info(
                "Cleaned up missing tracks",
                extra={"camera_id": self._settings.camera_id, "deleted": deleted},
            )
