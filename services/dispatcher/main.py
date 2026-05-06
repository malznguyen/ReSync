"""
Module: main
Service: dispatcher
Purpose: Start the Phase 6 event dispatcher service.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.dispatcher.config import DispatcherSettings
from services.dispatcher.consumer import EventDispatcher, RabbitMQConsumer
from services.dispatcher.http_poster import WebhookPoster
from services.dispatcher.logger import EventLogWriter
from services.dispatcher.logging_config import configure_logging
from services.dispatcher.repository import WebhookRepository

logger = logging.getLogger(__name__)


async def async_main() -> int:
    settings = DispatcherSettings.from_env()
    configure_logging(settings.log_level)

    shutdown_event = asyncio.Event()
    _install_signal_handlers(shutdown_event)

    engine = create_async_engine(settings.postgres_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    log_writer = EventLogWriter(session_factory)
    poster = WebhookPoster(settings.http_timeout_seconds)
    dispatcher = EventDispatcher(
        repository=WebhookRepository(session_factory),
        poster=poster,
        log_writer=log_writer,
        max_retries=settings.max_retries,
        retry_backoff_seconds=settings.retry_backoff_seconds,
    )
    consumer = RabbitMQConsumer(settings, dispatcher, log_writer)

    try:
        await consumer.run(shutdown_event)
    except KeyboardInterrupt:
        shutdown_event.set()
    except Exception:
        logger.exception("Dispatcher service crashed")
        raise
    finally:
        await consumer.aclose()
        await poster.aclose()
        await log_writer.aclose()
        await engine.dispose()

    return 0


def _install_signal_handlers(shutdown_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()

    def handle_signal(signum: int, _frame: object) -> None:
        logger.info("Received shutdown signal", extra={"signal": signum})
        loop.call_soon_threadsafe(shutdown_event.set)

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
