"""
Module: main
Service: ai_worker
Purpose: Start the Phase 3 AI detect-and-track worker.
"""

from __future__ import annotations

import logging
import signal
import threading

from config import AiWorkerSettings
from logging_config import configure_logging
from worker import run_worker

logger = logging.getLogger(__name__)


def main() -> int:
    settings = AiWorkerSettings.from_env()
    configure_logging(settings.log_level)

    shutdown_event = threading.Event()
    _install_signal_handlers(shutdown_event)

    try:
        run_worker(settings, shutdown_event)
    except KeyboardInterrupt:
        shutdown_event.set()
    except Exception:
        logger.exception("AI worker crashed", extra={"camera_id": settings.camera_id})
        raise

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
