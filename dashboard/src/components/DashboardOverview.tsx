"use client";

import {
  Activity,
  Camera,
  Hand,
  Map,
  RadioTower,
  UserCheck,
  type LucideIcon
} from "lucide-react";
import Link from "next/link";
import useSWR from "swr";

import { CameraStatusBadge } from "@/components/camera/CameraStatusBadge";
import { EventTypeBadge } from "@/components/event-feed/EventTypeBadge";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { getCameras, getEvents, getZones } from "@/lib/api";
import { formatTime, normalizeStatus } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  tone: string;
}

function MetricCard({
  label,
  value,
  icon: Icon,
  tone
}: MetricCardProps): JSX.Element {
  return (
    <Panel>
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-ink-500">
            {label}
          </p>
          <p className="mt-3 text-3xl font-black text-ink-900">{value}</p>
        </div>
        <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${tone}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      </div>
    </Panel>
  );
}

export function DashboardOverview(): JSX.Element {
  const camerasQuery = useSWR("cameras", getCameras, { refreshInterval: 5000 });
  const zonesQuery = useSWR("zones", () => getZones(), { refreshInterval: 10000 });
  const eventsQuery = useSWR("events-overview", () => getEvents(undefined, 8), {
    refreshInterval: 2000
  });

  const cameras = camerasQuery.data ?? [];
  const zones = zonesQuery.data ?? [];
  const events = eventsQuery.data?.items ?? [];
  const onlineCameras = cameras.filter(
    (camera) => normalizeStatus(camera.status) === "online"
  ).length;
  const handRaises = events.filter((event) => event.event_type === "hand_raise").length;
  const seated = events.filter(
    (event) => event.event_type === "customer_seated"
  ).length;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Online cameras"
          value={`${onlineCameras}/${cameras.length}`}
          icon={Camera}
          tone="bg-lagoon-100 text-lagoon-600"
        />
        <MetricCard
          label="Active zones"
          value={String(zones.filter((zone) => zone.active).length)}
          icon={Map}
          tone="bg-copper-100 text-copper-600"
        />
        <MetricCard
          label="Hand raises"
          value={String(handRaises)}
          icon={Hand}
          tone="bg-blue-50 text-blue-700"
        />
        <MetricCard
          label="Seated events"
          value={String(seated)}
          icon={UserCheck}
          tone="bg-emerald-50 text-emerald-700"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Panel>
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-lagoon-600">
                Camera fleet
              </p>
              <h2 className="mt-2 text-xl font-black text-ink-900">
                Stream health
              </h2>
            </div>
            <Link
              href="/cameras"
              className="text-sm font-black text-lagoon-600 transition hover:text-lagoon-400"
            >
              Manage
            </Link>
          </div>

          <div className="mt-5 divide-y divide-ink-900/10">
            {cameras.length ? (
              cameras.slice(0, 6).map((camera) => (
                <div
                  key={camera.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-4"
                >
                  <div>
                    <p className="font-black text-ink-900">{camera.name}</p>
                    <p className="mt-1 break-all text-sm text-ink-500">
                      {camera.rtsp_url}
                    </p>
                  </div>
                  <CameraStatusBadge status={camera.status} />
                </div>
              ))
            ) : (
              <EmptyState
                icon={Camera}
                title="No cameras"
                description="Configured streams will appear in this health view."
              />
            )}
          </div>
        </Panel>

        <Panel className="p-0">
          <div className="flex items-center justify-between border-b border-ink-900/10 px-5 py-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-copper-600">
                Event pulse
              </p>
              <h2 className="mt-2 text-xl font-black text-ink-900">
                Latest signals
              </h2>
            </div>
            <Badge tone="neutral">
              <RadioTower className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
              Live
            </Badge>
          </div>
          <div className="divide-y divide-ink-900/10">
            {events.length ? (
              events.map((event) => (
                <div key={event.id} className="px-5 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <EventTypeBadge eventType={event.event_type} />
                    <time className="text-xs font-bold text-ink-500">
                      {formatTime(event.timestamp)}
                    </time>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-ink-500">
                    Camera {event.camera_id ?? "unknown"} in zone{" "}
                    {event.zone_id ?? "unknown"}
                  </p>
                </div>
              ))
            ) : (
              <div className="p-5">
                <EmptyState
                  icon={Activity}
                  title="No recent events"
                  description="Realtime analytics signals will appear here."
                />
              </div>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
