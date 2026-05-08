"use client";

import {
  Brain,
  Cpu,
  Power,
  RefreshCw,
  Settings,
  Video,
  type LucideIcon
} from "lucide-react";
import { useMemo, useState } from "react";
import useSWR from "swr";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import {
  getSystemStatus,
  toggleInference,
  toggleMockCamera,
  toggleReid
} from "@/lib/api";
import type { SystemStatus } from "@/types/api";

type ControlId = "inference" | "reid" | "mock-camera";

interface ControlDefinition {
  id: ControlId;
  title: string;
  label: string;
  icon: LucideIcon;
  enabled: boolean;
  disabled?: boolean;
  status: string;
  detail: string;
}

const CONTROL_REFRESH_MS = 3000;

export function SystemControls(): JSX.Element {
  const [pendingControl, setPendingControl] = useState<ControlId | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const query = useSWR("system-status", getSystemStatus, {
    refreshInterval: CONTROL_REFRESH_MS
  });

  const controls = useMemo(() => {
    if (!query.data) {
      return [];
    }
    return buildControls(query.data);
  }, [query.data]);

  const applyToggle = async (
    controlId: ControlId,
    enabled: boolean
  ): Promise<void> => {
    if (!query.data) {
      return;
    }

    setPendingControl(controlId);
    setErrorMessage(null);
    try {
      await query.mutate(() => toggleById(controlId, enabled), {
        optimisticData: optimisticStatus(query.data, controlId, enabled),
        rollbackOnError: true,
        populateCache: true,
        revalidate: false
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Request failed");
    } finally {
      setPendingControl(null);
    }
  };

  if (query.error) {
    return (
      <EmptyState
        icon={RefreshCw}
        title="System controls unavailable"
        description="The dashboard could not load runtime control state."
        action={
          <Button onClick={() => void query.mutate()}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-5">
      <Panel className="overflow-hidden p-0">
        <div className="border-b border-ink-900/10 px-5 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-lagoon-600">
                Runtime state
              </p>
              <h2 className="mt-2 text-xl font-black text-ink-900">
                Developer & System Controls
              </h2>
            </div>
            <Badge tone={query.isLoading ? "amber" : "green"}>
              <Settings className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
              {query.isLoading ? "Syncing" : "Live"}
            </Badge>
          </div>
        </div>

        <div className="divide-y divide-ink-900/10">
          {query.isLoading && !query.data
            ? [Cpu, Brain, Video].map((Icon, index) => (
                <div
                  key={String(index)}
                  className="grid gap-4 px-5 py-5 md:grid-cols-[minmax(0,1fr)_auto]"
                >
                  <div className="flex gap-4">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-white/80 text-ink-500">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="h-5 w-44 animate-pulse rounded bg-white/80" />
                      <div className="mt-3 h-4 w-full max-w-sm animate-pulse rounded bg-white/60" />
                    </div>
                  </div>
                  <div className="h-9 w-20 animate-pulse rounded-full bg-white/80" />
                </div>
              ))
            : controls.map((control) => (
                <ControlRow
                  key={control.id}
                  control={control}
                  pending={pendingControl === control.id}
                  onToggle={(enabled) => void applyToggle(control.id, enabled)}
                />
              ))}
        </div>
      </Panel>

      {errorMessage ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
          {errorMessage}
        </div>
      ) : null}
    </div>
  );
}

function ControlRow({
  control,
  pending,
  onToggle
}: {
  control: ControlDefinition;
  pending: boolean;
  onToggle: (enabled: boolean) => void;
}): JSX.Element {
  const Icon = control.icon;

  return (
    <div className="grid gap-4 px-5 py-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
      <div className="flex min-w-0 gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-ink-900 text-white shadow-control">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-black text-ink-900">{control.title}</h3>
            <Badge tone={control.enabled ? "green" : "neutral"}>
              {control.status}
            </Badge>
          </div>
          <p className="mt-2 text-sm leading-6 text-ink-500">{control.detail}</p>
        </div>
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={control.enabled}
        aria-label={control.label}
        disabled={pending || control.disabled}
        onClick={() => onToggle(!control.enabled)}
        className="group inline-flex h-10 w-[76px] shrink-0 items-center rounded-full border border-ink-900/10 bg-white/80 p-1 shadow-sm transition disabled:pointer-events-none disabled:opacity-50 data-[checked=true]:bg-ink-900"
        data-checked={control.enabled}
      >
        <span className="flex h-8 w-8 translate-x-0 items-center justify-center rounded-full bg-ink-100 text-ink-500 shadow-sm transition group-data-[checked=true]:translate-x-9 group-data-[checked=true]:bg-lagoon-100 group-data-[checked=true]:text-ink-900">
          {pending ? (
            <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Power className="h-4 w-4" aria-hidden="true" />
          )}
        </span>
      </button>
    </div>
  );
}

function buildControls(status: SystemStatus): ControlDefinition[] {
  const mockDetail = status.mock_camera.detail
    ? status.mock_camera.detail
    : `${status.mock_camera.source_path} -> ${status.mock_camera.rtsp_url}`;

  return [
    {
      id: "inference",
      title: "AI Inference Engine",
      label: "Toggle AI Inference Engine",
      icon: Cpu,
      enabled: status.inference_enabled,
      status: status.inference_enabled ? "Processing" : "Paused",
      detail: status.inference_enabled
        ? "YOLO and ByteTrack are consuming the latest Redis frames."
        : "Frame processing is paused; ingestion can keep writing frames."
    },
    {
      id: "reid",
      title: "ReID Pipeline",
      label: "Toggle ReID Pipeline",
      icon: Brain,
      enabled: status.reid_enabled,
      status: status.reid_enabled ? "Matching" : "Bypassed",
      detail: status.reid_enabled
        ? "Customer vectors are matched after tracking."
        : "Tracks are written without customer identity matching."
    },
    {
      id: "mock-camera",
      title: "Mock Video Streamer",
      label: "Toggle Mock Video Streamer",
      icon: Video,
      enabled: status.mock_camera.enabled,
      disabled: !status.mock_camera.available,
      status: mockCameraStatusLabel(status),
      detail: mockDetail
    }
  ];
}

function mockCameraStatusLabel(status: SystemStatus): string {
  if (!status.mock_camera.available) {
    return "Unavailable";
  }
  if (status.mock_camera.running) {
    return "Streaming";
  }
  return status.mock_camera.enabled ? "Starting" : "Stopped";
}

function toggleById(
  controlId: ControlId,
  enabled: boolean
): Promise<SystemStatus> {
  if (controlId === "inference") {
    return toggleInference(enabled);
  }
  if (controlId === "reid") {
    return toggleReid(enabled);
  }
  return toggleMockCamera(enabled);
}

function optimisticStatus(
  status: SystemStatus,
  controlId: ControlId,
  enabled: boolean
): SystemStatus {
  if (controlId === "inference") {
    return { ...status, inference_enabled: enabled };
  }
  if (controlId === "reid") {
    return { ...status, reid_enabled: enabled };
  }
  return {
    ...status,
    mock_camera: {
      ...status.mock_camera,
      enabled,
      running: enabled ? status.mock_camera.running : false
    }
  };
}
