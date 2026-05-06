"""
Module: hand_raise
Service: analytics
Purpose: Detect sustained hand-raise poses from COCO keypoints.
"""

from __future__ import annotations

from services.ai_worker.schemas import Track

LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_HIP = 11
RIGHT_HIP = 12
CONFIDENCE_THRESHOLD = 0.5
TORSO_THRESHOLD_RATIO = 0.15


def is_hand_raised_pose(track: Track) -> bool:
    left_shoulder = track.keypoints[LEFT_SHOULDER]
    right_shoulder = track.keypoints[RIGHT_SHOULDER]
    left_hip = track.keypoints[LEFT_HIP]
    right_hip = track.keypoints[RIGHT_HIP]

    torso_points = (left_shoulder, right_shoulder, left_hip, right_hip)
    if any(point[2] < CONFIDENCE_THRESHOLD for point in torso_points):
        return False

    shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2.0
    hip_y = (left_hip[1] + right_hip[1]) / 2.0
    torso_height = abs(shoulder_y - hip_y)
    if torso_height <= 0.0:
        return False

    return _wrist_is_raised(track, LEFT_WRIST, LEFT_SHOULDER, torso_height) or (
        _wrist_is_raised(track, RIGHT_WRIST, RIGHT_SHOULDER, torso_height)
    )


def _wrist_is_raised(
    track: Track,
    wrist_index: int,
    shoulder_index: int,
    torso_height: float,
) -> bool:
    wrist = track.keypoints[wrist_index]
    shoulder = track.keypoints[shoulder_index]
    if wrist[2] < CONFIDENCE_THRESHOLD or shoulder[2] < CONFIDENCE_THRESHOLD:
        return False

    return wrist[1] < shoulder[1] - (TORSO_THRESHOLD_RATIO * torso_height)
