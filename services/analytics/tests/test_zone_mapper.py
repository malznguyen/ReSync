"""
Module: test_zone_mapper
Service: analytics
Purpose: Verify zone mapping uses hip anchors and Shapely polygons.
"""

from __future__ import annotations

from services.ai_worker.schemas import Track, ZoneConfig
from services.analytics.zone_mapper import ZoneMapper, track_position


def test_track_position_uses_hip_centroid() -> None:
    track = _make_track(
        bbox=(0.7, 0.7, 0.2, 0.2),
        left_hip=(0.2, 0.4, 0.9),
        right_hip=(0.4, 0.6, 0.9),
    )

    assert track_position(track) == (0.30000000000000004, 0.5)


def test_track_position_falls_back_to_bbox_center_when_both_hips_low() -> None:
    track = _make_track(
        bbox=(0.7, 0.6, 0.2, 0.2),
        left_hip=(0.2, 0.4, 0.2),
        right_hip=(0.4, 0.6, 0.1),
    )

    assert track_position(track) == (0.7999999999999999, 0.7)


def test_zone_mapper_matches_polygon_containing_hip_anchor() -> None:
    mapper = ZoneMapper(
        [
            ZoneConfig(
                zone_id="zone-1",
                camera_id="camera-1",
                name="Table 1",
                polygon=[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)],
            )
        ]
    )
    track = _make_track(
        bbox=(0.8, 0.8, 0.1, 0.1),
        left_hip=(0.2, 0.2, 0.9),
        right_hip=(0.3, 0.3, 0.9),
    )

    match = mapper.match_track(track)

    assert match is not None
    assert match.zone_id == "zone-1"
    assert match.zone_name == "Table 1"


def _make_track(
    bbox: tuple[float, float, float, float],
    left_hip: tuple[float, float, float],
    right_hip: tuple[float, float, float],
) -> Track:
    keypoints = [(0.1, 0.1, 0.9)] * 17
    keypoints[0] = (0.95, 0.95, 0.99)
    keypoints[11] = left_hip
    keypoints[12] = right_hip
    return Track(
        track_id="track-1",
        bbox=bbox,
        keypoints=keypoints,
        confidence=0.9,
    )
