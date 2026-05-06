"""
Module: reid
Service: ai_worker
Purpose: Extract OSNet ReID embeddings and map live tracks to customer IDs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
import psycopg2
import torch
from psycopg2.extensions import connection as PgConnection
from redis import Redis
from redis.exceptions import RedisError
from schemas import Track

logger = logging.getLogger(__name__)

OSNET_MODEL_NAME = "osnet_x0_25"
REID_INPUT_HEIGHT = 256
REID_INPUT_WIDTH = 128
REID_VECTOR_DIM = 512
REID_MATCH_SIMILARITY_THRESHOLD = 0.85
TRACK_CUSTOMER_TTL_SECONDS = 300
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class OSNetFeatureExtractor:
    """Load OSNet and extract L2-normalized 512d embeddings."""

    def __init__(self, model_path: str, device_name: str | None) -> None:
        from torchreid.reid import models
        from torchreid.reid.utils import load_pretrained_weights

        self._device = resolve_torch_device(device_name)
        weight_path = Path(model_path)
        has_weight_file = weight_path.exists()

        self._model = models.build_model(
            OSNET_MODEL_NAME,
            num_classes=1,
            loss="softmax",
            pretrained=not has_weight_file,
            use_gpu=self._device.type == "cuda",
        )
        if has_weight_file:
            load_pretrained_weights(self._model, str(weight_path))
        else:
            logger.warning(
                "Configured OSNet weights not found; using torchreid pretrained weights",
                extra={"model_path": model_path},
            )

        self._model.to(self._device)
        self._model.eval()

    def extract(self, crop_tensor: torch.Tensor) -> np.ndarray:
        batch = crop_tensor.unsqueeze(0).to(self._device)
        with torch.inference_mode():
            features = self._model(batch)

        vector = features.squeeze(0).detach().cpu().numpy()
        return normalize_feature_vector(vector)


class CustomerRepository:
    """Find or create customers in ai_core.customers using pgvector cosine distance."""

    def __init__(
        self,
        connection: PgConnection,
        similarity_threshold: float = REID_MATCH_SIMILARITY_THRESHOLD,
    ) -> None:
        self._connection = connection
        self._similarity_threshold = similarity_threshold

    def find_or_create_customer(self, vector: Sequence[float]) -> str:
        vector_literal = format_pgvector(vector)

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id::text, vector <=> %s::vector AS distance
                    FROM ai_core.customers
                    ORDER BY vector <=> %s::vector ASC
                    LIMIT 1
                    """,
                    (vector_literal, vector_literal),
                )
                row = cursor.fetchone()

                if row is not None:
                    customer_id, cosine_distance = row
                    if is_matching_customer(
                        float(cosine_distance),
                        self._similarity_threshold,
                    ):
                        cursor.execute(
                            """
                            UPDATE ai_core.customers
                            SET last_seen = NOW()
                            WHERE id = %s::uuid
                            """,
                            (str(customer_id),),
                        )
                        self._connection.commit()
                        return str(customer_id)

                cursor.execute(
                    """
                    INSERT INTO ai_core.customers (vector)
                    VALUES (%s::vector)
                    RETURNING id::text
                    """,
                    (vector_literal,),
                )
                inserted = cursor.fetchone()
                if inserted is None:
                    raise RuntimeError("Customer insert did not return an id")

                self._connection.commit()
                return str(inserted[0])
        except Exception:
            self._connection.rollback()
            logger.exception("Failed to match or create ReID customer")
            raise


class RedisTrackCustomerStore:
    """Store track-to-customer mappings with the required track TTL."""

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def save(self, track_id: str, customer_id: str) -> None:
        key = f"track:{track_id}:customer_id"
        try:
            self._redis.set(key, customer_id, ex=TRACK_CUSTOMER_TTL_SECONDS)
        except RedisError as exc:
            raise RuntimeError(
                f"Failed to store customer mapping for track {track_id}"
            ) from exc


class ReIDPipeline:
    """Run crop, preprocess, embedding, customer match, and Redis mapping."""

    def __init__(
        self,
        extractor: OSNetFeatureExtractor,
        repository: CustomerRepository,
        store: RedisTrackCustomerStore,
    ) -> None:
        self._extractor = extractor
        self._repository = repository
        self._store = store

    def identify_tracks(self, frame_bytes: bytes, tracks: list[Track]) -> list[Track]:
        if not tracks:
            return tracks

        frame = decode_frame(frame_bytes)
        identified_tracks: list[Track] = []
        for track in tracks:
            crop = crop_person(frame, track)
            if crop is None:
                logger.warning(
                    "Skipping ReID for track with invalid bbox",
                    extra={"track_id": track.track_id, "bbox": track.bbox},
                )
                identified_tracks.append(track)
                continue

            crop_tensor = preprocess_crop(crop)
            vector = self._extractor.extract(crop_tensor)
            customer_id = self._repository.find_or_create_customer(vector)
            self._store.save(track.track_id, customer_id)
            identified_tracks.append(
                track.model_copy(update={"customer_id": customer_id})
            )

        return identified_tracks


def create_postgres_connection(postgres_dsn: str) -> PgConnection:
    connection = psycopg2.connect(postgres_dsn)
    connection.autocommit = False
    return connection


def decode_frame(frame_bytes: bytes) -> np.ndarray:
    encoded = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Failed to decode frame bytes as an image")
    return frame


def crop_person(frame: np.ndarray, track: Track) -> np.ndarray | None:
    frame_height, frame_width = frame.shape[:2]
    x, y, width, height = track.bbox
    if width <= 0.0 or height <= 0.0:
        return None

    x1 = int(np.floor(x * frame_width))
    y1 = int(np.floor(y * frame_height))
    x2 = int(np.ceil((x + width) * frame_width))
    y2 = int(np.ceil((y + height) * frame_height))

    x1 = int(np.clip(x1, 0, frame_width))
    y1 = int(np.clip(y1, 0, frame_height))
    x2 = int(np.clip(x2, 0, frame_width))
    y2 = int(np.clip(y2, 0, frame_height))

    if x2 <= x1 or y2 <= y1:
        return None

    return frame[y1:y2, x1:x2]


def preprocess_crop(crop: np.ndarray) -> torch.Tensor:
    resized = cv2.resize(
        crop,
        (REID_INPUT_WIDTH, REID_INPUT_HEIGHT),
        interpolation=cv2.INTER_LINEAR,
    )
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255.0)
    mean = torch.tensor(IMAGENET_MEAN, dtype=torch.float32).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD, dtype=torch.float32).view(3, 1, 1)
    return (tensor - mean) / std


def normalize_feature_vector(vector: Sequence[float]) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float32).reshape(-1)
    if array.shape != (REID_VECTOR_DIM,):
        raise ValueError(f"Expected {REID_VECTOR_DIM}d ReID vector, got {array.size}d")

    norm = float(np.linalg.norm(array))
    if not np.isfinite(norm) or norm <= 0.0:
        raise ValueError("Cannot normalize empty or non-finite ReID vector")

    return (array / norm).astype(np.float32)


def format_pgvector(vector: Sequence[float]) -> str:
    array = np.asarray(vector, dtype=np.float32).reshape(-1)
    if array.shape != (REID_VECTOR_DIM,):
        raise ValueError(f"Expected {REID_VECTOR_DIM}d ReID vector, got {array.size}d")

    norm = float(np.linalg.norm(array))
    if not np.isclose(norm, 1.0, rtol=1e-3, atol=1e-3):
        raise ValueError("ReID vector must be L2-normalized before database use")

    return "[" + ",".join(f"{float(value):.8f}" for value in array) + "]"


def cosine_similarity_from_distance(cosine_distance: float) -> float:
    return 1.0 - cosine_distance


def is_matching_customer(
    cosine_distance: float,
    similarity_threshold: float = REID_MATCH_SIMILARITY_THRESHOLD,
) -> bool:
    return cosine_similarity_from_distance(cosine_distance) > similarity_threshold


def resolve_torch_device(device_name: str | None) -> torch.device:
    if device_name is None or device_name.strip() == "":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    normalized_name = device_name.strip().lower()
    if normalized_name.isdigit():
        normalized_name = f"cuda:{normalized_name}"

    device = torch.device(normalized_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        logger.warning(
            "CUDA requested for ReID but unavailable; falling back to CPU",
            extra={"requested_device": device_name},
        )
        return torch.device("cpu")

    return device
