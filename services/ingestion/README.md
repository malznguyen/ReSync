# Ingestion Service

Phase 2 reads active camera RTSP streams from `config.cameras`, decodes one stream per process, JPEG-encodes each frame, and atomically overwrites these Redis keys:

- `cam:{camera_id}:frame:latest`
- `cam:{camera_id}:frame:meta`

The service attempts the GStreamer RTSP pipeline first:

```text
rtspsrc ! rtph264depay ! avdec_h264 ! videoconvert ! appsink
```

If OpenCV was not built with GStreamer support or the pipeline cannot open, it immediately falls back to `cv2.VideoCapture`.

## Local Smoke Test

Start infrastructure and apply Phase 1 storage migrations:

```bash
docker compose up -d --build postgres redis mediamtx
docker compose run --rm storage_tools sh -lc "python -m pip install -r api/requirements.txt && python -m alembic upgrade head"
docker compose run --rm storage_tools sh -lc "python -m pip install -r api/requirements.txt && python scripts/seed_dev.py"
```

Publish a looping test stream to MediaMTX from the host:

```bash
ffmpeg -re -stream_loop -1 -f lavfi -i testsrc=size=1280x720:rate=30 -c:v libx264 -pix_fmt yuv420p -f rtsp rtsp://localhost:8554/demo
```

Activate the seeded dummy camera:

```bash
docker compose exec postgres psql -U vision_user -d vision_system -c "UPDATE config.cameras SET status='active' WHERE id='00000000-0000-0000-0000-000000000101';"
```

Run ingestion with the optional Compose profile:

```bash
docker compose --profile ingestion up --build ingestion
```

Confirm Redis has the latest frame and metadata:

```bash
docker compose exec redis redis-cli HGETALL cam:00000000-0000-0000-0000-000000000101:frame:meta
docker compose exec redis redis-cli STRLEN cam:00000000-0000-0000-0000-000000000101:frame:latest
```
