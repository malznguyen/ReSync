# Todo and Testing

## Task 1: Create a Fake Camera Script

Create `scripts/start_fake_camera.sh` with the following contents:

```bash
#!/usr/bin/env bash
set -euo pipefail

ffmpeg -re -stream_loop -1 -i demo.mp4 -c copy -f rtsp rtsp://localhost:8554/test
```

This loops `demo.mp4` forever and publishes it as an RTSP stream to MediaMTX at:

```text
rtsp://localhost:8554/test
```

If the codec copy path fails, replace `-c copy` with the fallback encoder flags:

```bash
ffmpeg -re -stream_loop -1 -i demo.mp4 -c:v libx264 -preset ultrafast -f rtsp rtsp://localhost:8554/test
```

## Task 2: Manual UI Testing Steps

1. Start the Docker Compose stack from the repository root:

   ```bash
   make up
   ```

   If `make` is unavailable, use:

   ```bash
   docker compose up -d
   ```

2. Run the fake camera script in the background:

   ```bash
   ./scripts/start_fake_camera.sh > /tmp/fake-camera.log 2>&1 &
   ```

3. Start the Mock Webhook Server:

   ```bash
   python e2e_tests/mock_webhook.py
   ```

4. Log in to the Dashboard:

   ```text
   http://localhost:3000
   ```

5. Add a camera in the Dashboard UI using the internal Docker DNS RTSP URL:

   ```text
   rtsp://mediamtx:8554/test
   ```

6. Add the webhook endpoint in the Dashboard UI:

   ```text
   http://host.docker.internal:8001/webhook
   ```

7. Open the Zone Painter tool, watch the HLS stream, and draw a polygon over the seats.

8. Save the zone and confirm the zone change takes effect without restarting services.

9. Open the Realtime Events Feed.

10. Verify that `CUSTOMER_SEATED` events trigger after a customer remains seated in the zone.

11. Verify that `HAND_RAISE` events trigger when a seated customer raises a hand.

12. Confirm that the Mock Webhook Server receives the expected webhook payloads.

## Success Criteria

- The fake RTSP stream is visible through MediaMTX/HLS.
- The Dashboard can create the camera using `rtsp://mediamtx:8554/test`.
- The Dashboard can create the webhook using `http://host.docker.internal:8001/webhook`.
- The Zone Painter saves a polygon over the seating area.
- `CUSTOMER_SEATED` appears in the Realtime Events Feed.
- `HAND_RAISE` appears in the Realtime Events Feed.
- The Mock Webhook Server receives matching webhook deliveries.
