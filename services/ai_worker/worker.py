"""
Module: worker
Service: ai_worker
Purpose: Coordinate Redis frame reads, YOLO tracking, validation, and Redis writes.
"""

from __future__ import annotations

import logging
import threading
import time

from config import AiWorkerSettings
from detector import PoseTracker
from metrics import ProcessingMetrics
from redis_io import RedisFrameReader, RedisTrackWriter, create_redis_client
from schemas import FrameMetadata, TrackOutput

logger = logging.getLogger(__name__)


def run_worker(settings: AiWorkerSettings, shutdown_event: threading.Event) -> None:
    redis_client = create_redis_client(
        settings.redis_url,
        settings.redis_socket_timeout_seconds,
    )
    reader = RedisFrameReader(redis_client)
    writer = RedisTrackWriter(redis_client)
    tracker = PoseTracker(
        model_path=settings.yolo_model_path,
        tracker_config_path=settings.tracker_config_path,
        confidence_threshold=settings.yolo_confidence_threshold,
        iou_threshold=settings.yolo_iou_threshold,
        image_size=settings.yolo_image_size,
        device=settings.yolo_device,
    )
    metrics = ProcessingMetrics(settings.fps_log_interval_seconds, logger)
    last_observed_frame_id: str | None = None

    logger.info("Started AI worker", extra={"camera_id": settings.camera_id})
    try:
        while not shutdown_event.is_set():
            read_started_at = time.monotonic()
            frame = reader.read_latest(settings.camera_id)
            if frame is None:
                shutdown_event.wait(settings.poll_interval_seconds)
                continue

            metadata = frame.metadata
            if metadata.frame_id == last_observed_frame_id:
                shutdown_event.wait(settings.poll_interval_seconds)
                continue

            last_observed_frame_id = metadata.frame_id
            now_epoch = time.time()
            frame_age_seconds = now_epoch - metadata.timestamp
            if is_stale_frame(
                metadata,
                now_epoch,
                settings.stale_frame_seconds,
            ):
                logger.warning(
                    "Skipping stale frame",
                    extra={
                        "camera_id": metadata.camera_id,
                        "frame_id": metadata.frame_id,
                        "frame_age_seconds": round(frame_age_seconds, 3),
                        "stale_threshold_seconds": settings.stale_frame_seconds,
                    },
                )
                continue

            tracks = tracker.track(frame.frame_bytes)
            output = TrackOutput(
                frame_id=metadata.frame_id,
                timestamp=metadata.timestamp,
                camera_id=metadata.camera_id,
                tracks=tracks,
            )
            writer.write_tracks(output)

            processed_at = time.monotonic()
            latency_seconds = processed_at - read_started_at
            metrics.record(processed_at, latency_seconds)
            metrics.log_if_due(
                camera_id=metadata.camera_id,
                frame_id=metadata.frame_id,
                track_count=len(tracks),
                timestamp=processed_at,
            )
    finally:
        redis_client.close()
        logger.info("Stopped AI worker", extra={"camera_id": settings.camera_id})


def is_stale_frame(
    metadata: FrameMetadata,
    now: float,
    stale_after_seconds: float,
) -> bool:
    return now - metadata.timestamp > stale_after_seconds
