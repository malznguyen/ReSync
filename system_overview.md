# System Overview

## System Purpose

The AI Restaurant Vision System is a real-time behavioral event detection platform for restaurants. It watches camera streams, detects people, tracks customer movement, identifies restaurant-specific behaviors such as customers sitting down or raising a hand for service, and dispatches webhook events to external POS or service systems.

The system is optimized for low-latency event detection, not general CCTV recording or playback.

## Architecture & Data Flow

The production data path is strictly one-way:

```text
Camera → Redis → AI → Redis → Analytics → RabbitMQ → Dispatcher → Internet
```

This boundary is enforced to keep the pipeline deterministic and avoid hard-to-debug race conditions. Ingestion writes frames to Redis, AI workers read those frames and write track outputs back to Redis, analytics consumes track outputs and publishes business events to RabbitMQ, and the dispatcher sends those events to external webhooks.

The dispatcher must not read directly from Redis, and analytics must not create a back-channel to ingestion.

Administrative control flows separately through the Dashboard UI and Control API. The dashboard calls the API over HTTP, the API persists configuration in PostgreSQL, and Redis Pub/Sub is used only to notify runtime services that camera or zone configuration changed.

## Microservices Map

| Microservice | Directory | Role | Core Tech Stack |
|---|---|---|---|
| Ingestion | `services/ingestion` | Connects to RTSP camera streams, decodes frames, and writes the latest frame and metadata to Redis. | Python 3.11, GStreamer, OpenCV fallback, Redis |
| AI Worker | `services/ai_worker` | Runs pose detection, tracking, and customer re-identification, then writes normalized track outputs to Redis. | Python 3.11, YOLOv8 Pose, ByteTrack, OSNet ReID, Redis, Pydantic |
| State Analytics | `services/analytics` | Maps tracks into zones, maintains per-track state, detects seated and hand-raise events, and publishes events. | Python 3.11, Shapely, state machines, Redis, PostgreSQL, RabbitMQ |
| Webhook Dispatcher | `services/dispatcher` | Consumes event messages and delivers signed webhook payloads with retry and logging. | Python 3.11, RabbitMQ, httpx, HMAC-SHA256, PostgreSQL |
| Control API | `api` | Provides authenticated CRUD endpoints for cameras, zones, webhooks, and analytics data. | Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis |
| Dashboard UI | `dashboard` | Browser admin interface for camera setup, zone painting, event monitoring, and analytics views. | Next.js 14, React, TypeScript, Canvas zone painter, HLS playback |

## Storage Layer

### PostgreSQL

PostgreSQL is the durable source of truth for configuration and historical business data. It stores cameras, zones, webhooks, visits, and event records. It also contains the `ai_core.customers` table with pgvector embeddings for ReID matching.

Customer ReID uses cosine distance through pgvector's `<=>` operator, with normalized OSNet vectors. HNSW indexing is used for reliable approximate nearest-neighbor search from the first inserted row.

### Redis

Redis is the real-time coordination layer. It stores the latest frame and metadata per camera, the latest AI track output per camera, short-lived per-track state keys, customer ID mappings, and cached zone configuration.

It also provides Pub/Sub channels for configuration invalidation, such as camera reloads and zone updates. Redis is a speed optimization and live pipeline buffer; long-term configuration and event history belong in PostgreSQL.

### RabbitMQ

RabbitMQ is the reliable event queue between analytics and webhook delivery. Analytics publishes business events to the durable `events` topic exchange, and dispatcher consumers read from the `webhook_dispatch` queue.

Manual acknowledgments are required so events are acknowledged only after processing. Failed webhook deliveries should be retried or routed to the dead-letter queue instead of being silently lost.
