"""
Module: worker
Service: ai_worker
Purpose: Coordinate Redis frame reads, YOLO tracking, ReID, and Redis writes.
"""

from __future__ import annotations

import logging
import threading
import time

import overlay
import reid
from config import AiWorkerSettings
from detector import PoseTracker
from metrics import ProcessingMetrics
from redis_io import (
    RedisFrameReader,
    RedisOverlayWriter,
    RedisTrackWriter,
    create_redis_client,
)
from schemas import FrameMetadata, TrackOutput

logger = logging.getLogger(__name__)


def run_worker(settings: AiWorkerSettings, shutdown_event: threading.Event) -> None:
    redis_client = create_redis_client(
        settings.redis_url,
        settings.redis_socket_timeout_seconds,
    )
    postgres_connection = (
        reid.create_postgres_connection(settings.postgres_dsn)
        if settings.reid_enabled and settings.postgres_dsn is not None
        else None
    )
    reader = RedisFrameReader(redis_client)
    writer = RedisTrackWriter(redis_client)
    overlay_writer = RedisOverlayWriter(redis_client)
    tracker = PoseTracker(
        model_path=settings.yolo_model_path,
        tracker_config_path=settings.tracker_config_path,
        confidence_threshold=settings.yolo_confidence_threshold,
        iou_threshold=settings.yolo_iou_threshold,
        image_size=settings.yolo_image_size,
        device=settings.yolo_device,
    )
    reid_pipeline = (
        reid.ReIDPipeline(
            extractor=reid.OSNetFeatureExtractor(
                model_path=settings.osnet_model_path,
                device_name=settings.yolo_device,
            ),
            repository=reid.CustomerRepository(postgres_connection),
            store=reid.RedisTrackCustomerStore(redis_client),
        )
        if postgres_connection is not None
        else None
    )
    metrics = ProcessingMetrics(settings.fps_log_interval_seconds, logger)
    last_observed_frame_id: str | None = None

    logger.info(
        "Started AI worker",
        extra={
            "camera_id": settings.camera_id,
            "reid_enabled": reid_pipeline is not None,
            "inference_device": settings.yolo_device,
        },
    )
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
            if reid_pipeline is not None:
                tracks = reid_pipeline.identify_tracks(frame.frame_bytes, tracks)

            output = TrackOutput(
                frame_id=metadata.frame_id,
                timestamp=metadata.timestamp,
                camera_id=metadata.camera_id,
                tracks=tracks,
            )
            writer.write_tracks(output)
            try:
                overlay_bytes = overlay.render_overlay_frame(frame.frame_bytes, tracks)
                overlay_writer.write_overlay(
                    camera_id=metadata.camera_id,
                    frame_id=metadata.frame_id,
                    timestamp=metadata.timestamp,
                    frame_bytes=overlay_bytes,
                )
            except Exception:
                logger.exception(
                    "Failed to render monitoring overlay frame",
                    extra={
                        "camera_id": metadata.camera_id,
                        "frame_id": metadata.frame_id,
                    },
                )

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
        if postgres_connection is not None:
            postgres_connection.close()
        redis_client.close()
        logger.info("Stopped AI worker", extra={"camera_id": settings.camera_id})


def is_stale_frame(
    metadata: FrameMetadata,
    now: float,
    stale_after_seconds: float,
) -> bool:
    return now - metadata.timestamp > stale_after_seconds
