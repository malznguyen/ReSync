"use client";

import {
  CircleCheck,
  MonitorPlay,
  RefreshCw,
  Video
} from "lucide-react";
import { useMemo, useState } from "react";
import useSWR from "swr";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { getCameraTracks, getCameras } from "@/lib/api";
import {
  getHlsStreamUrl,
  getRtspStreamPath,
  normalizeStatus
} from "@/lib/utils";
import type { Camera } from "@/types/api";

interface LiveStreamCardProps {
  camera: Camera;
}

function LiveStreamCard({ camera }: LiveStreamCardProps): JSX.Element {
  const [playbackError, setPlaybackError] = useState<string | undefined>();
  const streamPath = getRtspStreamPath(camera.rtsp_url);
  const rawStreamUrl = getHlsStreamUrl(camera.rtsp_url);
  const overlayStreamUrl = `/api/cameras/${camera.id}/overlay/stream`;
  const { data: trackOutput, error: trackError } = useSWR(
    ["camera-tracks", camera.id],
    () => getCameraTracks(camera.id),
    {
      refreshInterval: 1000,
      dedupingInterval: 500,
      keepPreviousData: true
    }
  );
  const tracks = trackOutput?.tracks ?? [];

  return (
    <Panel className="overflow-hidden p-0">
      <div className="relative aspect-video bg-ink-900">
        {/* MJPEG monitoring streams need a plain img element to preserve the multipart response. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={overlayStreamUrl}
          alt={`${camera.name} annotated monitoring stream`}
          className="h-full w-full object-contain"
          onError={() => setPlaybackError("Annotated monitoring stream unavailable.")}
          onLoad={() => setPlaybackError(undefined)}
        />
        <div className="absolute left-3 top-3">
          <Badge tone="green" className="bg-emerald-50/95">
            <CircleCheck className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Online
          </Badge>
        </div>
        <div className="absolute right-3 top-3 z-20">
          <Badge tone={trackError ? "red" : tracks.length ? "blue" : "amber"}>
            {trackError
              ? "AI unavailable"
              : tracks.length
                ? `${tracks.length} tracks`
                : "AI pending"}
          </Badge>
        </div>
        {playbackError ? (
          <div className="absolute inset-x-4 bottom-4 rounded-lg border border-copper-600/20 bg-[#fffdf6]/92 px-3 py-2 text-sm font-bold text-copper-600 shadow-control">
            {playbackError}
          </div>
        ) : null}
      </div>
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-lagoon-600">
              Live feed
            </p>
            <h2 className="mt-2 truncate text-xl font-black text-ink-900">
              {camera.name}
            </h2>
          </div>
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-lagoon-100 text-lagoon-600">
            <Video className="h-5 w-5" aria-hidden="true" />
          </div>
        </div>
        <dl className="mt-4 grid gap-3 border-t border-ink-900/10 pt-4 text-sm">
          <div>
            <dt className="font-bold text-ink-900">Stream path</dt>
            <dd className="mt-1 break-all text-ink-500">{streamPath || "Unavailable"}</dd>
          </div>
          <div>
            <dt className="font-bold text-ink-900">Annotated stream</dt>
            <dd className="mt-1 break-all text-ink-500">{overlayStreamUrl}</dd>
          </div>
          <div>
            <dt className="font-bold text-ink-900">Raw HLS URL</dt>
            <dd className="mt-1 break-all text-ink-500">{rawStreamUrl}</dd>
          </div>
          <div>
            <dt className="font-bold text-ink-900">AI frame</dt>
            <dd className="mt-1 break-all text-ink-500">
              {trackOutput?.frame_id || "Waiting for YOLO output"}
            </dd>
          </div>
        </dl>
      </div>
    </Panel>
  );
}

export default function StreamsPage(): JSX.Element {
  const { data, error, isLoading, mutate } = useSWR("cameras", getCameras, {
    refreshInterval: 5000
  });

  const activeCameras = useMemo(
    () =>
      (data ?? []).filter(
        (camera) => normalizeStatus(camera.status) === "online"
      ),
    [data]
  );

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Live Streams"
          description="Watch active restaurant camera feeds from the MediaMTX HLS endpoint."
        />
        <div className="grid gap-5 xl:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Panel key={index} className="h-96 animate-pulse bg-white/60" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Live Streams"
          description="Watch active restaurant camera feeds from the MediaMTX HLS endpoint."
        />
        <EmptyState
          icon={RefreshCw}
          title="Stream data unavailable"
          description="The dashboard could not load active cameras from the Control API."
          action={
            <Button onClick={() => void mutate()}>
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Retry
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Live Streams"
        description="Watch active restaurant camera feeds from the MediaMTX HLS endpoint."
      />

      {activeCameras.length ? (
        <div className="grid gap-5 xl:grid-cols-2">
          {activeCameras.map((camera) => (
            <LiveStreamCard key={camera.id} camera={camera} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={MonitorPlay}
          title="No active streams"
          description="Active cameras will appear here once the Control API reports them online."
        />
      )}
    </div>
  );
}
