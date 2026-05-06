"""
Module: test_reid
Service: ai_worker
Purpose: Verify OSNet ReID preprocessing, vector matching, and Redis mapping rules.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest
import reid
import torch
from schemas import Track


def test_crop_person_uses_normalized_bbox_coordinates() -> None:
    frame = np.arange(10 * 20 * 3, dtype=np.uint8).reshape(10, 20, 3)
    track = _make_track(bbox=(0.25, 0.2, 0.5, 0.6))

    crop = reid.crop_person(frame, track)

    assert crop is not None
    assert crop.shape == (6, 10, 3)
    np.testing.assert_array_equal(crop, frame[2:8, 5:15])


def test_preprocess_crop_resizes_before_imagenet_normalization() -> None:
    crop = np.zeros((4, 4, 3), dtype=np.uint8)
    crop[:, :, 2] = 255

    tensor = reid.preprocess_crop(crop)

    assert tuple(tensor.shape) == (3, 256, 128)
    expected_pixel = torch.tensor(
        [
            (1.0 - reid.IMAGENET_MEAN[0]) / reid.IMAGENET_STD[0],
            (0.0 - reid.IMAGENET_MEAN[1]) / reid.IMAGENET_STD[1],
            (0.0 - reid.IMAGENET_MEAN[2]) / reid.IMAGENET_STD[2],
        ],
        dtype=torch.float32,
    )
    assert torch.allclose(tensor[:, 0, 0], expected_pixel)


def test_normalize_feature_vector_returns_unit_512d_vector() -> None:
    vector = np.zeros(512, dtype=np.float32)
    vector[0] = 3.0
    vector[1] = 4.0

    normalized = reid.normalize_feature_vector(vector)

    assert normalized.shape == (512,)
    assert np.linalg.norm(normalized) == pytest.approx(1.0)
    assert normalized[0] == pytest.approx(0.6)
    assert normalized[1] == pytest.approx(0.8)


def test_format_pgvector_rejects_unnormalized_vectors() -> None:
    vector = np.ones(512, dtype=np.float32)

    with pytest.raises(ValueError, match="L2-normalized"):
        reid.format_pgvector(vector)


def test_cosine_match_requires_similarity_greater_than_threshold() -> None:
    assert reid.is_matching_customer(0.149)
    assert not reid.is_matching_customer(0.15)


def test_customer_repository_updates_matching_customer() -> None:
    vector = _normalized_vector()
    connection = FakeConnection(fetch_results=[("customer-1", 0.1)])
    repository = reid.CustomerRepository(connection)

    customer_id = repository.find_or_create_customer(vector)

    assert customer_id == "customer-1"
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert "<=>" in connection.cursor_instance.statements[0][0]
    assert "UPDATE ai_core.customers" in connection.cursor_instance.statements[1][0]


def test_customer_repository_inserts_when_similarity_is_too_low() -> None:
    vector = _normalized_vector()
    connection = FakeConnection(fetch_results=[("customer-1", 0.2), ("customer-2",)])
    repository = reid.CustomerRepository(connection)

    customer_id = repository.find_or_create_customer(vector)

    assert customer_id == "customer-2"
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert (
        "INSERT INTO ai_core.customers" in connection.cursor_instance.statements[1][0]
    )


def test_reid_pipeline_assigns_customer_id_to_valid_track() -> None:
    frame = np.full((10, 20, 3), 255, dtype=np.uint8)
    encoded, frame_bytes = cv2.imencode(".jpg", frame)
    assert encoded
    track = _make_track(bbox=(0.25, 0.2, 0.5, 0.6))
    extractor = FakeExtractor()
    repository = FakeRepository()
    store = FakeStore()
    pipeline = reid.ReIDPipeline(extractor, repository, store)

    identified = pipeline.identify_tracks(frame_bytes.tobytes(), [track])

    assert identified[0].customer_id == "customer-1"
    assert tuple(extractor.seen_tensors[0].shape) == (3, 256, 128)
    assert store.calls == [("track-1", "customer-1")]


def test_redis_store_uses_exact_track_customer_ttl() -> None:
    redis_client = FakeRedis()
    store = reid.RedisTrackCustomerStore(redis_client)

    store.save("track-1", "customer-1")

    assert redis_client.calls == [
        ("track:track-1:customer_id", "customer-1", reid.TRACK_CUSTOMER_TTL_SECONDS)
    ]


def _make_track(bbox: tuple[float, float, float, float]) -> Track:
    return Track(
        track_id="track-1",
        bbox=bbox,
        keypoints=[(0.0, 0.0, 0.0)] * 17,
        confidence=0.9,
    )


def _normalized_vector() -> np.ndarray:
    vector = np.zeros(512, dtype=np.float32)
    vector[0] = 1.0
    return vector


class FakeCursor:
    def __init__(self, fetch_results: list[tuple[object, ...]]) -> None:
        self.fetch_results = fetch_results
        self.statements: list[tuple[str, tuple[object, ...]]] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc: object,
        _traceback: object,
    ) -> None:
        return None

    def execute(self, sql: str, params: tuple[object, ...]) -> None:
        self.statements.append((sql, params))

    def fetchone(self) -> tuple[object, ...] | None:
        if not self.fetch_results:
            return None
        return self.fetch_results.pop(0)


class FakeConnection:
    def __init__(self, fetch_results: list[tuple[object, ...]]) -> None:
        self.cursor_instance = FakeCursor(fetch_results)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeExtractor:
    def __init__(self) -> None:
        self.seen_tensors: list[torch.Tensor] = []

    def extract(self, crop_tensor: torch.Tensor) -> np.ndarray:
        self.seen_tensors.append(crop_tensor)
        return _normalized_vector()


class FakeRepository:
    def find_or_create_customer(self, vector: np.ndarray) -> str:
        assert np.linalg.norm(vector) == pytest.approx(1.0)
        return "customer-1"


class FakeStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def save(self, track_id: str, customer_id: str) -> None:
        self.calls.append((track_id, customer_id))


class FakeRedis:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def set(self, key: str, value: str, ex: int) -> None:
        self.calls.append((key, value, ex))
