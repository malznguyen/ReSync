"""
Module: main
Service: analytics
Purpose: Start the Phase 5 state analytics engine.
"""

from __future__ import annotations

import logging
import signal
import threading

from services.analytics.config import AnalyticsSettings
from services.analytics.db import ZoneRepository
from services.analytics.engine import AnalyticsEngine
from services.analytics.event_publisher import RabbitMQEventPublisher
from services.analytics.logging_config import configure_logging
from services.analytics.redis_io import (
    RedisTrackReader,
    RedisTrackStateStore,
    create_redis_client,
)
from services.analytics.state_machine import TrackStateMachine
from services.analytics.zone_cache import ZoneConfigCache

logger = logging.getLogger(__name__)


def main() -> int:
    settings = AnalyticsSettings.from_env()
    configure_logging(settings.log_level)

    shutdown_event = threading.Event()
    _install_signal_handlers(shutdown_event)

    redis_client = create_redis_client(
        settings.redis_url,
        settings.redis_socket_timeout_seconds,
    )
    repository = ZoneRepository(settings.postgres_dsn)
    state_store = RedisTrackStateStore(redis_client)
    state_machine = TrackStateMachine(
        store=state_store,
        seated_threshold_seconds=settings.seated_threshold_seconds,
        hand_raise_threshold_seconds=settings.hand_raise_threshold_seconds,
        hand_raise_cooldown_seconds=settings.hand_raise_cooldown_seconds,
    )
    engine = AnalyticsEngine(
        settings=settings,
        reader=RedisTrackReader(redis_client),
        state_store=state_store,
        zone_cache=ZoneConfigCache(
            repository=repository,
            redis_client=redis_client,
            refresh_interval_seconds=settings.zone_cache_refresh_seconds,
        ),
        state_machine=state_machine,
        publisher=RabbitMQEventPublisher(
            host=settings.rabbitmq_host,
            port=settings.rabbitmq_port,
            user=settings.rabbitmq_user,
            password=settings.rabbitmq_password,
        ),
    )

    try:
        engine.run(shutdown_event)
    except KeyboardInterrupt:
        shutdown_event.set()
    except Exception:
        logger.exception(
            "Analytics service crashed", extra={"camera_id": settings.camera_id}
        )
        raise
    finally:
        redis_client.close()

    return 0


def _install_signal_handlers(shutdown_event: threading.Event) -> None:
    def handle_signal(signum: int, _frame: object) -> None:
        logger.info("Received shutdown signal", extra={"signal": signum})
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)


if __name__ == "__main__":
    raise SystemExit(main())
