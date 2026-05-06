"""
Module: health_check
Service: infra
Purpose: Verify Postgres, Redis, and RabbitMQ connectivity in parallel.
"""

from __future__ import annotations

import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pika
import psycopg
import redis

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.core.config import get_rabbitmq_url  # noqa: E402
from api.core.config import get_postgres_url, get_redis_url

logger = logging.getLogger(__name__)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }
        for field in ("service", "status", "detail"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        return json.dumps(payload, sort_keys=True)


@dataclass(frozen=True)
class CheckResult:
    service: str
    ok: bool
    detail: str


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logging.getLogger("pika").setLevel(logging.WARNING)


def check_postgres() -> CheckResult:
    with psycopg.connect(
        get_postgres_url(driver="postgresql"), connect_timeout=5
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            database, user = cursor.fetchone()
    return CheckResult("postgres", True, f"connected database={database} user={user}")


def check_redis() -> CheckResult:
    client = redis.Redis.from_url(
        get_redis_url(),
        socket_connect_timeout=5,
        socket_timeout=5,
        decode_responses=True,
    )
    pong = client.ping()
    keyspace_events = client.config_get("notify-keyspace-events").get(
        "notify-keyspace-events", ""
    )
    return CheckResult(
        "redis",
        bool(pong),
        f"ping={pong} notify-keyspace-events={keyspace_events or 'disabled'}",
    )


def check_rabbitmq() -> CheckResult:
    parameters = pika.URLParameters(get_rabbitmq_url())
    parameters.blocked_connection_timeout = 5
    parameters.connection_attempts = 1
    parameters.socket_timeout = 5
    connection = pika.BlockingConnection(parameters)
    try:
        channel = connection.channel()
        channel.exchange_declare(
            exchange="events",
            exchange_type="topic",
            durable=True,
            passive=True,
        )
        for queue_name in ("hand_raise", "customer_seated", "webhook_retry", "dlq"):
            channel.queue_declare(queue=queue_name, passive=True)
    finally:
        connection.close()
    return CheckResult(
        "rabbitmq",
        True,
        "events exchange and Phase 1 queues are reachable",
    )


def run_check(name: str, check: Callable[[], CheckResult]) -> CheckResult:
    try:
        return check()
    except Exception as exc:
        return CheckResult(name, False, f"{type(exc).__name__}: {exc}")


def main() -> int:
    configure_logging()
    checks: dict[str, Callable[[], CheckResult]] = {
        "postgres": check_postgres,
        "redis": check_redis,
        "rabbitmq": check_rabbitmq,
    }

    results: list[CheckResult] = []
    with ThreadPoolExecutor(max_workers=len(checks)) as executor:
        futures = {
            executor.submit(run_check, name, check): name
            for name, check in checks.items()
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            logger.info(
                "health_check",
                extra={
                    "service": result.service,
                    "status": "ok" if result.ok else "failed",
                    "detail": result.detail,
                },
            )

    ok = all(result.ok for result in results)
    logger.info(
        "health_check_summary",
        extra={
            "service": "storage",
            "status": "ok" if ok else "failed",
            "detail": f"{sum(result.ok for result in results)}/{len(results)} checks passed",
        },
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
