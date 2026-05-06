"""
Module: zone_mapper
Service: analytics
Purpose: Map tracked people to configured zones using Shapely polygons.
"""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree

from services.ai_worker.schemas import Track, ZoneConfig

LEFT_HIP = 11
RIGHT_HIP = 12
HIP_CONFIDENCE_THRESHOLD = 0.5


@dataclass(frozen=True)
class ZoneMatch:
    zone_id: str
    camera_id: str
    zone_name: str


@dataclass(frozen=True)
class IndexedZone:
    config: ZoneConfig
    polygon: Polygon


class ZoneMapper:
    """Map track hip anchors to zones from an immutable zone snapshot."""

    def __init__(self, zones: list[ZoneConfig]) -> None:
        self._zones = [
            IndexedZone(config=zone, polygon=zone.to_shapely()) for zone in zones
        ]
        self._tree = STRtree([zone.polygon for zone in self._zones])

    def match_track(self, track: Track) -> ZoneMatch | None:
        point = Point(track_position(track))
        for zone_index in self._tree.query(point):
            zone = self._zones[int(zone_index)]
            if zone.polygon.covers(point):
                return ZoneMatch(
                    zone_id=zone.config.zone_id,
                    camera_id=zone.config.camera_id,
                    zone_name=zone.config.name,
                )
        return None


def track_position(track: Track) -> tuple[float, float]:
    left_hip = track.keypoints[LEFT_HIP]
    right_hip = track.keypoints[RIGHT_HIP]

    if (
        left_hip[2] < HIP_CONFIDENCE_THRESHOLD
        and right_hip[2] < HIP_CONFIDENCE_THRESHOLD
    ):
        x, y, width, height = track.bbox
        return x + width / 2.0, y + height / 2.0

    return (left_hip[0] + right_hip[0]) / 2.0, (left_hip[1] + right_hip[1]) / 2.0
