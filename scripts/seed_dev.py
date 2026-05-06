"""
Module: seed_dev
Service: infra
Purpose: Insert deterministic development seed data for local storage checks.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.core.config import get_postgres_url  # noqa: E402

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def seed_camera() -> str:
    camera_id = "00000000-0000-0000-0000-000000000101"
    statement = text("""
        INSERT INTO config.cameras (id, name, rtsp_url, status)
        VALUES (:id, :name, :rtsp_url, :status)
        ON CONFLICT (id) DO UPDATE
        SET name = EXCLUDED.name,
            rtsp_url = EXCLUDED.rtsp_url,
            status = EXCLUDED.status
        RETURNING id
        """)

    engine = create_engine(get_postgres_url(), pool_pre_ping=True)
    with engine.begin() as connection:
        inserted_id = connection.execute(
            statement,
            {
                "id": camera_id,
                "name": "Demo Dining Room Camera",
                "rtsp_url": "rtsp://mediamtx:8554/demo",
                "status": "inactive",
            },
        ).scalar_one()
    return str(inserted_id)


def main() -> int:
    configure_logging()
    camera_id = seed_camera()
    logger.info("Seeded config.cameras record", extra={"camera_id": camera_id})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
