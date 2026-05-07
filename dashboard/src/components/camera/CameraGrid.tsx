"use client";

import { ArrowUpRight, Camera, Plus, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";

import { AddCameraModal } from "@/components/camera/AddCameraModal";
import { CameraStatusBadge } from "@/components/camera/CameraStatusBadge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { getCameras } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import type { Camera as CameraType } from "@/types/api";

export function CameraGrid(): JSX.Element {
  const [modalOpen, setModalOpen] = useState(false);
  const { data, error, isLoading, mutate } = useSWR("cameras", getCameras, {
    refreshInterval: 5000
  });

  const cameras = data ?? [];

  const handleCreated = (camera: CameraType): void => {
    void mutate([camera, ...cameras], {
      optimisticData: [camera, ...cameras],
      rollbackOnError: true,
      revalidate: true
    });
  };

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <Panel key={index} className="h-52 animate-pulse bg-white/60" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        icon={RefreshCw}
        title="Camera data unavailable"
        description="The dashboard could not load camera configuration from the Control API."
        action={
          <Button onClick={() => void mutate()}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <>
      {cameras.length === 0 ? (
        <EmptyState
          icon={Camera}
          title="No cameras configured"
          description="Add the first restaurant stream to begin zone setup and event monitoring."
          action={
            <Button onClick={() => setModalOpen(true)}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Camera
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => setModalOpen(true)}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Camera
            </Button>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {cameras.map((camera) => (
              <Panel
                key={camera.id}
                className="group flex min-h-52 flex-col justify-between transition duration-200 hover:-translate-y-1 hover:shadow-panel"
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-lagoon-100 text-lagoon-600">
                      <Camera className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <CameraStatusBadge status={camera.status} />
                  </div>
                  <h2 className="mt-5 text-xl font-black text-ink-900">
                    {camera.name}
                  </h2>
                  <p className="mt-2 break-all text-sm leading-6 text-ink-500">
                    {camera.rtsp_url}
                  </p>
                </div>
                <div className="mt-5 flex items-center justify-between border-t border-ink-900/10 pt-4">
                  <span className="text-xs font-semibold text-ink-500">
                    Added {formatDateTime(camera.created_at)}
                  </span>
                  <Link
                    href={`/zones/${camera.id}`}
                    className="inline-flex items-center gap-1 text-sm font-black text-lagoon-600 transition hover:text-lagoon-400"
                  >
                    Zones
                    <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </div>
              </Panel>
            ))}
          </div>
        </div>
      )}

      <AddCameraModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={handleCreated}
      />
    </>
  );
}
