"""
Module: test_detector
Service: ai_worker
Purpose: Verify detector conversion helpers keep bbox and keypoints normalized.
"""

from __future__ import annotations

import numpy as np
from detector import format_keypoints, normalize_xyxy_bbox


def test_normalize_xyxy_bbox_returns_normalized_xywh() -> None:
    bbox = normalize_xyxy_bbox(
        np.array([100.0, 50.0, 500.0, 250.0]),
        width=1000,
        height=500,
    )

    assert bbox == (0.1, 0.1, 0.4, 0.4)


def test_format_keypoints_marks_low_confidence_as_missing() -> None:
    points = np.full((1, 17, 2), 0.5)
    confidences = np.ones((1, 17))
    points[0, 9] = [0.25, 0.1]
    confidences[0, 9] = 0.49

    keypoints = format_keypoints((points, confidences), track_index=0)

    assert len(keypoints) == 17
    assert keypoints[9] == (0.0, 0.0, 0.0)
    assert keypoints[10] == (0.5, 0.5, 1.0)
