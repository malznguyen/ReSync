"""
Module: test_overlay
Service: ai_worker
Purpose: Verify backend overlay rendering uses the processed AI frame geometry.
"""

from __future__ import annotations

import cv2
import numpy as np

from overlay import normalized_bbox_to_pixels, render_overlay_frame
from schemas import Track


def test_normalized_bbox_to_pixels_scales_to_frame_bounds() -> None:
    pixels = normalized_bbox_to_pixels((0.25, 0.1, 0.5, 0.4), 200, 100)

    assert pixels == (50, 10, 150, 50)


def test_render_overlay_frame_draws_on_processed_frame() -> None:
    frame = np.zeros((80, 120, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", frame)
    assert success
    track = Track(
        track_id="7",
        bbox=(0.25, 0.2, 0.35, 0.5),
        keypoints=[(0.5, 0.5, 0.0)] * 17,
        confidence=0.82,
    )

    rendered = render_overlay_frame(encoded.tobytes(), [track])
    decoded = cv2.imdecode(np.frombuffer(rendered, dtype=np.uint8), cv2.IMREAD_COLOR)

    assert decoded is not None
    assert decoded.shape == frame.shape
    assert int(decoded.sum()) > 0
