"""
Module: zone_cache
Service: analytics
Purpose: Cache Postgres zone config in Redis with Pub/Sub and periodic refresh.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict

from redis import Redis
from redis.exceptions import RedisError

from services.ai_worker.schemas import ZoneConfig
from services.analytics.db import ZoneRepository
from services.analytics.zone_mapper import ZoneMapper

ZONE_CACHE_KEY = "zone:config:cache"
ZONE_UPDATE_CHANNEL = "zone:config:updated"

logger = logging.getLogger(__name__)


class ZoneConfigCache:
    """Keep an in-memory Shapely snapshot synchronized from Postgres."""

    def __init__(
        self,
        repository: ZoneRepository,
        redis_client: Redis,
        refresh_interval_seconds: float,
    ) -> None:
        self._repository = repository
        self._redis = redis_client
        self._refresh_interval_seconds = refresh_interval_seconds
        self._lock = threading.RLock()
        self._mappers_by_camera: dict[str, ZoneMapper] = {}

    def refresh(self) -> None:
        zones = self._repository.list_active_zones()
        payload = json.dumps(
            [zone.model_dump(mode="json") for zone in zones],
            separators=(",", ":"),
        )

        try:
            self._redis.set(ZONE_CACHE_KEY, payload)
        except RedisError as exc:
            raise RuntimeError("Failed to cache zone configuration in Redis") from exc

        mappers_by_camera = _build_mappers(zones)
        with self._lock:
            self._mappers_by_camera = mappers_by_camera

        logger.info("Refreshed zone config", extra={"zone_count": len(zones)})

    def get_mapper(self, camera_id: str) -> ZoneMapper | None:
        with self._lock:
            return self._mappers_by_camera.get(camera_id)

    def start_background_refresh(
        self,
        shutdown_event: threading.Event,
    ) -> list[threading.Thread]:
        threads = [
            threading.Thread(
                target=self._run_periodic_refresh,
                args=(shutdown_event,),
                name="zone-cache-periodic-refresh",
                daemon=True,
            ),
            threading.Thread(
                target=self._run_pubsub_listener,
                args=(shutdown_event,),
                name="zone-cache-pubsub-listener",
                daemon=True,
            ),
        ]
        for thread in threads:
            thread.start()
        return threads

    def _run_periodic_refresh(self, shutdown_event: threading.Event) -> None:
        while not shutdown_event.wait(self._refresh_interval_seconds):
            try:
                self.refresh()
            except Exception:
                logger.exception("Periodic zone config refresh failed")

    def _run_pubsub_listener(self, shutdown_event: threading.Event) -> None:
        while not shutdown_event.is_set():
            try:
                with self._redis.pubsub(ignore_subscribe_messages=True) as pubsub:
                    pubsub.subscribe(ZONE_UPDATE_CHANNEL)
                    while not shutdown_event.is_set():
                        message = pubsub.get_message(timeout=1.0)
                        if message is None:
                            continue
                        logger.info("Received zone config update notification")
                        self.refresh()
            except RedisError:
                logger.exception("Zone config Pub/Sub listener failed")
                shutdown_event.wait(1.0)


def _build_mappers(zones: list[ZoneConfig]) -> dict[str, ZoneMapper]:
    zones_by_camera: dict[str, list[ZoneConfig]] = defaultdict(list)
    for zone in zones:
        zones_by_camera[zone.camera_id].append(zone)

    return {
        camera_id: ZoneMapper(camera_zones)
        for camera_id, camera_zones in zones_by_camera.items()
    }
