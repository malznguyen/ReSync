"use client";

import Hls from "hls.js";
import {
  Check,
  CircleDot,
  Eraser,
  Loader2,
  MousePointer2,
  Save
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Panel } from "@/components/ui/Panel";
import { createZone, getCameras, getZones } from "@/lib/api";
import { getHlsStreamUrl } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { Camera, Point, Zone } from "@/types/api";

interface ZonePainterProps {
  cameraId: string;
}

interface CanvasSize {
  width: number;
  height: number;
}

interface VideoRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

const DRAFT_FILL = "rgba(74, 169, 160, 0.24)";
const DRAFT_STROKE = "rgba(29, 109, 104, 0.94)";
const SAVED_FILL = "rgba(199, 119, 81, 0.18)";
const SAVED_STROKE = "rgba(150, 71, 44, 0.78)";

function getVideoRect(
  canvas: CanvasSize,
  videoWidth: number,
  videoHeight: number
): VideoRect {
  if (videoWidth <= 0 || videoHeight <= 0 || canvas.width <= 0 || canvas.height <= 0) {
    return {
      x: 0,
      y: 0,
      width: canvas.width,
      height: canvas.height
    };
  }

  const scale = Math.min(canvas.width / videoWidth, canvas.height / videoHeight);
  const width = videoWidth * scale;
  const height = videoHeight * scale;

  return {
    x: (canvas.width - width) / 2,
    y: (canvas.height - height) / 2,
    width,
    height
  };
}

function clamp(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function pointToCanvas(point: Point, rect: VideoRect): Point {
  return [rect.x + point[0] * rect.width, rect.y + point[1] * rect.height];
}

function drawPolygon(
  context: CanvasRenderingContext2D,
  points: Point[],
  rect: VideoRect,
  fillStyle: string,
  strokeStyle: string
): void {
  if (points.length < 2) {
    return;
  }

  const [firstX, firstY] = pointToCanvas(points[0], rect);
  context.beginPath();
  context.moveTo(firstX, firstY);
  points.slice(1).forEach((point) => {
    const [x, y] = pointToCanvas(point, rect);
    context.lineTo(x, y);
  });
  if (points.length >= 3) {
    context.closePath();
    context.fillStyle = fillStyle;
    context.fill();
  }
  context.strokeStyle = strokeStyle;
  context.lineWidth = 2;
  context.stroke();
}

function distance(a: Point, b: Point): number {
  return Math.hypot(a[0] - b[0], a[1] - b[1]);
}

function pointerToNormalizedPoint(
  event: React.PointerEvent<HTMLCanvasElement>,
  rect: VideoRect
): Point | null {
  const bounds = event.currentTarget.getBoundingClientRect();
  const x = event.clientX - bounds.left;
  const y = event.clientY - bounds.top;

  if (
    x < rect.x ||
    x > rect.x + rect.width ||
    y < rect.y ||
    y > rect.y + rect.height
  ) {
    return null;
  }

  return [clamp((x - rect.x) / rect.width), clamp((y - rect.y) / rect.height)];
}

function closePolygon(points: Point[]): Point[] {
  if (points.length === 0) {
    return [];
  }
  const [firstX, firstY] = points[0];
  return [...points, [firstX, firstY]];
}

export function ZonePainter({ cameraId }: ZonePainterProps): JSX.Element {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [canvasSize, setCanvasSize] = useState<CanvasSize>({ width: 0, height: 0 });
  const [vertices, setVertices] = useState<Point[]>([]);
  const [activeVertex, setActiveVertex] = useState<number | null>(null);
  const [zoneName, setZoneName] = useState("Dining Zone");
  const [message, setMessage] = useState<string | undefined>();
  const [error, setError] = useState<string | undefined>();
  const [isSaving, setIsSaving] = useState(false);

  const streamUrl = getHlsStreamUrl(cameraId);
  const camerasQuery = useSWR("cameras", getCameras, { refreshInterval: 5000 });
  const zonesQuery = useSWR(["zones", cameraId], () => getZones(cameraId), {
    refreshInterval: 10000
  });

  const camera = useMemo<Camera | undefined>(
    () => camerasQuery.data?.find((item) => item.id === cameraId),
    [cameraId, camerasQuery.data]
  );

  const videoRect = useMemo(() => {
    const video = videoRef.current;
    return getVideoRect(
      canvasSize,
      video?.videoWidth ?? 0,
      video?.videoHeight ?? 0
    );
  }, [canvasSize]);

  const redraw = useCallback((): void => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }

    const ratio = window.devicePixelRatio || 1;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, canvasSize.width, canvasSize.height);

    context.fillStyle = "rgba(23, 26, 18, 0.34)";
    context.fillRect(0, 0, canvasSize.width, canvasSize.height);
    context.clearRect(videoRect.x, videoRect.y, videoRect.width, videoRect.height);

    zonesQuery.data?.forEach((zone) => {
      drawPolygon(context, zone.polygon, videoRect, SAVED_FILL, SAVED_STROKE);
    });

    drawPolygon(context, vertices, videoRect, DRAFT_FILL, DRAFT_STROKE);

    vertices.forEach((point, index) => {
      const [x, y] = pointToCanvas(point, videoRect);
      context.beginPath();
      context.arc(x, y, 6, 0, Math.PI * 2);
      context.fillStyle = index === activeVertex ? "#171a12" : "#fffdf6";
      context.fill();
      context.lineWidth = 2;
      context.strokeStyle = DRAFT_STROKE;
      context.stroke();
    });
  }, [activeVertex, canvasSize, vertices, videoRect, zonesQuery.data]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) {
      return undefined;
    }

    if (Hls.isSupported()) {
      const hls = new Hls({
        lowLatencyMode: true,
        backBufferLength: 30
      });
      hls.loadSource(streamUrl);
      hls.attachMedia(video);
      return () => hls.destroy();
    }

    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = streamUrl;
    }

    return undefined;
  }, [streamUrl]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return undefined;
    }

    const resize = (): void => {
      const bounds = canvas.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.round(bounds.width * ratio);
      canvas.height = Math.round(bounds.height * ratio);
      setCanvasSize({ width: bounds.width, height: bounds.height });
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    window.addEventListener("resize", resize);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", resize);
    };
  }, []);

  useEffect(() => {
    redraw();
  }, [redraw]);

  const findVertex = (point: Point): number | null => {
    const threshold = 14;
    const canvasPoint = pointToCanvas(point, videoRect);
    const match = vertices.findIndex((vertex) => {
      const existing = pointToCanvas(vertex, videoRect);
      return distance(canvasPoint, existing) <= threshold;
    });
    return match >= 0 ? match : null;
  };

  const handlePointerDown = (
    event: React.PointerEvent<HTMLCanvasElement>
  ): void => {
    const point = pointerToNormalizedPoint(event, videoRect);
    if (!point) {
      return;
    }

    const existingIndex = findVertex(point);
    if (existingIndex !== null) {
      setActiveVertex(existingIndex);
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }

    setVertices((current) => [...current, point]);
    setMessage(undefined);
    setError(undefined);
  };

  const handlePointerMove = (
    event: React.PointerEvent<HTMLCanvasElement>
  ): void => {
    if (activeVertex === null) {
      return;
    }

    const point = pointerToNormalizedPoint(event, videoRect);
    if (!point) {
      return;
    }

    setVertices((current) =>
      current.map((vertex, index) => (index === activeVertex ? point : vertex))
    );
  };

  const clearDraft = (): void => {
    setVertices([]);
    setActiveVertex(null);
    setMessage(undefined);
    setError(undefined);
  };

  const handleSave = async (): Promise<void> => {
    setError(undefined);
    setMessage(undefined);

    if (vertices.length < 3) {
      setError("Draw at least three vertices before saving.");
      return;
    }

    setIsSaving(true);
    try {
      const zone = await createZone({
        camera_id: cameraId,
        name: zoneName.trim() || "Dining Zone",
        polygon: closePolygon(vertices),
        active: true
      });
      await zonesQuery.mutate([zone, ...(zonesQuery.data ?? [])], {
        optimisticData: [zone, ...(zonesQuery.data ?? [])],
        rollbackOnError: true,
        revalidate: true
      });
      setVertices([]);
      setMessage("Zone saved with normalized coordinates.");
    } catch (caughtError) {
      setError(
        caughtError instanceof Error ? caughtError.message : "Unable to save zone."
      );
    } finally {
      setIsSaving(false);
    }
  };

  if (camerasQuery.isLoading || zonesQuery.isLoading) {
    return (
      <Panel className="flex min-h-96 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-lagoon-600" aria-hidden="true" />
      </Panel>
    );
  }

  if (!camera) {
    return (
      <EmptyState
        icon={CircleDot}
        title="Camera not found"
        description="The selected camera is not available from the Control API."
      />
    );
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <Panel className="p-3">
        <div className="relative aspect-video overflow-hidden rounded-lg bg-ink-900">
          <video
            ref={videoRef}
            className="h-full w-full object-contain"
            muted
            playsInline
            autoPlay
            controls
            onLoadedMetadata={() => setCanvasSize((current) => ({ ...current }))}
          />
          <canvas
            ref={canvasRef}
            className="absolute inset-0 h-full w-full cursor-crosshair touch-none"
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={() => setActiveVertex(null)}
            onPointerCancel={() => setActiveVertex(null)}
            aria-label="Zone polygon canvas"
          />
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2 text-sm font-semibold text-ink-500">
            <Badge tone="neutral">
              <MousePointer2 className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
              {vertices.length} vertices
            </Badge>
            <span>{streamUrl}</span>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={clearDraft} disabled={!vertices.length}>
              <Eraser className="h-4 w-4" aria-hidden="true" />
              Clear
            </Button>
            <Button onClick={handleSave} disabled={isSaving || vertices.length < 3}>
              <Save className="h-4 w-4" aria-hidden="true" />
              {isSaving ? "Saving" : "Save Zone"}
            </Button>
          </div>
        </div>
      </Panel>

      <aside className="space-y-4">
        <Panel>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-lagoon-600">
            Camera
          </p>
          <h2 className="mt-2 text-2xl font-black text-ink-900">{camera.name}</h2>
          <p className="mt-2 break-all text-sm leading-6 text-ink-500">
            {camera.rtsp_url}
          </p>
        </Panel>

        <Panel className="space-y-4">
          <Input
            label="Zone name"
            name="zone-name"
            value={zoneName}
            onChange={(event) => setZoneName(event.target.value)}
          />
          {message ? (
            <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">
              <Check className="h-4 w-4" aria-hidden="true" />
              {message}
            </div>
          ) : null}
          {error ? (
            <div className="rounded-lg border border-copper-600/20 bg-copper-100/45 px-3 py-2 text-sm font-semibold text-copper-600">
              {error}
            </div>
          ) : null}
        </Panel>

        <Panel>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-black text-ink-900">Saved zones</h2>
            <Badge tone="neutral">{zonesQuery.data?.length ?? 0}</Badge>
          </div>
          <div className="mt-4 space-y-3">
            {zonesQuery.data?.length ? (
              zonesQuery.data.map((zone) => (
                <div
                  key={zone.id}
                  className={cn(
                    "rounded-lg border border-ink-900/10 bg-white/70 p-3",
                    zone.active ? "opacity-100" : "opacity-60"
                  )}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-bold text-ink-900">{zone.name}</p>
                    <Badge tone={zone.active ? "green" : "neutral"}>
                      {zone.active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs font-semibold text-ink-500">
                    {Math.max(0, zone.polygon.length - 1)} points
                  </p>
                </div>
              ))
            ) : (
              <p className="rounded-lg border border-dashed border-ink-900/15 bg-white/55 p-4 text-sm leading-6 text-ink-500">
                No zones saved for this camera yet.
              </p>
            )}
          </div>
        </Panel>
      </aside>
    </div>
  );
}
