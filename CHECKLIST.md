# Phase 9 MVP Sign-off Checklist

Current status: Phase 8 is DONE. Phase 9 is IN PROGRESS.

Use this checklist as the final MVP gate. Check an item only after running the listed validation against the current stack.

## Runtime Prerequisites

- [ ] `.env` contains a real `JWT_SECRET` with at least 32 characters.
- [ ] `.env` contains a real `API_ADMIN_PASSWORD_HASH`; plaintext admin passwords are only supplied through local shell env for tests.
- [ ] Docker stack is running with `api`, `ingestion`, `ai_worker`, `analytics`, `dispatcher`, `postgres`, `redis`, `rabbitmq`, and `mediamtx`.
- [ ] `demo.mp4` exists at the repo root and contains a clear seated customer and hand-raise sequence.
- [ ] `TEST_WEBHOOK_SECRET` or `E2E_TEST_WEBHOOK_SECRET` is set to the same value used by the mock webhook and registered webhook.
- [ ] Mock webhook is running on the host with `python e2e_tests/mock_webhook.py`.
- [ ] Registered webhook URL is `http://host.docker.internal:8001/webhook` for Docker Desktop on Windows/Mac.
- [ ] `AI_WORKER_CAMERA_ID` and `ANALYTICS_CAMERA_ID` are aligned with the camera under test, or the E2E test failure is treated as a real integration blocker.

## MVP Definition

- [ ] Test video stream runs through the full pipeline.
  Validation: `pytest e2e_tests/test_e2e_pipeline.py -m e2e`.
- [ ] `HAND_RAISE` appears in `analytics.events` within the test window.
  Validation: E2E test finds `hand_raise` for the API-created camera.
- [ ] `CUSTOMER_SEATED` fires after the seated threshold.
  Validation: E2E test finds `customer_seated` for the API-created camera.
- [ ] Webhook receives correct payload with valid HMAC-SHA256 signature.
  Validation: mock webhook logs `Signature Verify Pass`.
- [ ] Admin can add a camera without touching the database.
  Validation: E2E test creates the camera via `POST /cameras`.
- [ ] Admin can draw and save a zone polygon.
  Validation: E2E test creates a normalized whole-frame polygon via `POST /zones`.
- [ ] Zone change takes effect without service restart.
  Validation: analytics logs `Received zone config update notification` or refreshes within the configured fallback window.
- [ ] System runs stable for 30 minutes with two simultaneous streams.
  Validation: run two MediaMTX paths and monitor service restarts, queue depth, CPU, and memory.
- [ ] No hardcoded secrets are tracked.
  Validation: run a secret scan and review `.env.example` placeholders separately from real `.env`.
- [ ] All service logs are structured JSON with no raw `print()` service output.
  Validation: inspect service logs and search Python service files for `print(`.
- [ ] `make test` passes with greater than 70 percent coverage on analytics and dispatcher.
  Validation: run the project test target with coverage enabled.

## Security And Operations

- [ ] JWT uses only `HS256` and rejects missing, placeholder, or short secrets.
- [ ] API admin authentication uses a password hash, not a tracked plaintext password.
- [ ] Webhook signing uses HMAC-SHA256 over the exact POST body bytes.
- [ ] Dispatcher uses manual RabbitMQ acknowledgment and dead-letter routing for failed dispatches.
- [ ] Redis keys follow the documented `cam:*`, `track:*`, and `zone:config:*` patterns.
- [ ] AI worker skips stale frames older than the configured threshold.
- [ ] Analytics zone config has both Pub/Sub invalidation and periodic refresh fallback.
- [ ] Postgres pgvector matching uses cosine distance `<=>` and normalized vectors.
- [ ] Load test completes without API 5xx spikes, OOM restarts, or runaway database connections.
  Validation: `k6 run e2e_tests/load_test.js`.
