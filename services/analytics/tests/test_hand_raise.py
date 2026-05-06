"""
Module: test_hand_raise
Service: analytics
Purpose: Verify hand-raise posture logic follows normalized y-axis rules.
"""

from __future__ import annotations

from services.ai_worker.schemas import Track
from services.analytics.detectors.hand_raise import is_hand_raised_pose


def test_hand_raise_true_when_wrist_is_above_shoulder_threshold() -> None:
    track = _make_pose(left_wrist_y=0.44, right_wrist_y=0.7)

    assert is_hand_raised_pose(track) is True


def test_hand_raise_false_when_wrist_is_not_above_threshold() -> None:
    track = _make_pose(left_wrist_y=0.46, right_wrist_y=0.7)

    assert is_hand_raised_pose(track) is False


def test_hand_raise_false_when_torso_keypoints_are_low_confidence() -> None:
    track = _make_pose(left_wrist_y=0.44, right_wrist_y=0.7, hip_confidence=0.2)

    assert is_hand_raised_pose(track) is False


def _make_pose(
    left_wrist_y: float,
    right_wrist_y: float,
    hip_confidence: float = 0.9,
) -> Track:
    keypoints = [(0.1, 0.1, 0.9)] * 17
    keypoints[5] = (0.3, 0.5, 0.9)
    keypoints[6] = (0.7, 0.5, 0.9)
    keypoints[9] = (0.3, left_wrist_y, 0.9)
    keypoints[10] = (0.7, right_wrist_y, 0.9)
    keypoints[11] = (0.3, 0.8, hip_confidence)
    keypoints[12] = (0.7, 0.8, hip_confidence)
    return Track(
        track_id="track-1",
        bbox=(0.2, 0.2, 0.5, 0.6),
        keypoints=keypoints,
        confidence=0.9,
    )
