#!/usr/bin/env bash
set -euo pipefail

ffmpeg -re -stream_loop -1 -i demo.mp4 -c copy -f rtsp rtsp://localhost:8554/test
