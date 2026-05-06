"""
Module: main
Service: ingestion
Purpose: Start the Phase 2 multi-camera video ingestion service.
"""

from __future__ import annotations

import logging
import multiprocessing
import signal
import threading

from camera_manager import CameraWatchdog
from config import IngestionSettings
from db import CameraRepository
from logging_config import configure_logging

logger = logging.getLogger(__name__)


def main() -> int:
    multiprocessing.freeze_support()
    settings = IngestionSettings.from_env()
    configure_logging(settings.log_level)

    shutdown_event = threading.Event()
    _install_signal_handlers(shutdown_event)

    repository = CameraRepository(settings.postgres_url)
    watchdog = CameraWatchdog(repository, settings, shutdown_event)
    watchdog.start()

    logger.info("Started ingestion service")
    try:
        while watchdog.is_alive():
            watchdog.join(timeout=1.0)
    except KeyboardInterrupt:
        shutdown_event.set()
    finally:
        shutdown_event.set()
        watchdog.join()
        logger.info("Stopped ingestion service")

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
