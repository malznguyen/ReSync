"""
Module: db
Service: analytics
Purpose: Load active zone polygon configuration from PostgreSQL.
"""

from __future__ import annotations

import json
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from services.ai_worker.schemas import ZoneConfig


class ZoneRepository:
    """Read active zone configuration owned by the config schema."""

    def __init__(self, postgres_dsn: str) -> None:
        self._postgres_dsn = postgres_dsn

    def list_active_zones(self) -> list[ZoneConfig]:
        statement = """
            SELECT id::text AS zone_id, camera_id::text AS camera_id, name, polygon
            FROM config.zones
            WHERE active = TRUE
            ORDER BY camera_id ASC, name ASC, id ASC
            """
        with psycopg2.connect(self._postgres_dsn) as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(statement)
                rows = cursor.fetchall()

        return [
            ZoneConfig(
                zone_id=str(row["zone_id"]),
                camera_id=str(row["camera_id"]),
                name=str(row["name"]),
                polygon=_coerce_polygon(row["polygon"]),
            )
            for row in rows
        ]


def _coerce_polygon(raw_polygon: Any) -> list[tuple[float, float]]:
    if isinstance(raw_polygon, str):
        raw_polygon = json.loads(raw_polygon)

    if not isinstance(raw_polygon, list):
        raise ValueError("zone polygon must be a JSON list of [x, y] points")

    return [(float(point[0]), float(point[1])) for point in raw_polygon]
