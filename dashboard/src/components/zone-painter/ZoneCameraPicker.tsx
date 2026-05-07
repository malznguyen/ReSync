"use client";

import { ArrowUpRight, Camera } from "lucide-react";
import Link from "next/link";
import useSWR from "swr";

import { CameraStatusBadge } from "@/components/camera/CameraStatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { getCameras } from "@/lib/api";

export function ZoneCameraPicker(): JSX.Element {
  const { data, isLoading } = useSWR("cameras", getCameras, {
    refreshInterval: 5000
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <Panel key={index} className="h-40 animate-pulse bg-white/60" />
        ))}
      </div>
    );
  }

  if (!data?.length) {
    return (
      <EmptyState
        icon={Camera}
        title="No cameras available"
        description="Add a camera before opening the zone painter."
      />
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {data.map((camera) => (
        <Link key={camera.id} href={`/zones/${camera.id}`} className="group">
          <Panel className="transition duration-200 group-hover:-translate-y-1 group-hover:shadow-panel">
            <div className="flex items-start justify-between gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-lagoon-100 text-lagoon-600">
                <Camera className="h-5 w-5" aria-hidden="true" />
              </div>
              <CameraStatusBadge status={camera.status} />
            </div>
            <h2 className="mt-5 text-xl font-black text-ink-900">{camera.name}</h2>
            <span className="mt-5 inline-flex items-center gap-1 text-sm font-black text-lagoon-600">
              Open painter
              <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </span>
          </Panel>
        </Link>
      ))}
    </div>
  );
}
