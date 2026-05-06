"""
Module: db
Service: ingestion
Purpose: Load active camera stream configuration from PostgreSQL.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class CameraConfig:
    camera_id: str
    name: str
    rtsp_url: str


class CameraRepository:
    """Read camera configuration owned by the config schema."""

    def __init__(self, postgres_url: str) -> None:
        self._engine: Engine = create_engine(postgres_url, pool_pre_ping=True)

    def list_active_cameras(self) -> list[CameraConfig]:
        statement = text("""
            SELECT id::text AS camera_id, name, rtsp_url
            FROM config.cameras
            WHERE lower(status) = 'active'
            ORDER BY created_at ASC
            """)
        with self._engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()

        return [
            CameraConfig(
                camera_id=str(row["camera_id"]),
                name=str(row["name"]),
                rtsp_url=str(row["rtsp_url"]),
            )
            for row in rows
        ]

    def close(self) -> None:
        self._engine.dispose()
