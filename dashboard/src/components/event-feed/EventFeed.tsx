"use client";

import { RadioTower, RefreshCw } from "lucide-react";
import useSWR from "swr";

import { EventTypeBadge } from "@/components/event-feed/EventTypeBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { getEvents } from "@/lib/api";
import { formatDateTime, titleCase } from "@/lib/utils";

export function EventFeed(): JSX.Element {
  const { data, error, isLoading, mutate } = useSWR(
    "events-feed",
    () => getEvents(undefined, 100),
    {
      refreshInterval: 2000
    }
  );

  if (isLoading) {
    return (
      <Panel className="h-[680px] animate-pulse bg-white/60" />
    );
  }

  if (error) {
    return (
      <EmptyState
        icon={RefreshCw}
        title="Event feed unavailable"
        description="The dashboard could not load realtime analytics events."
        action={
          <Button onClick={() => void mutate()}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Retry
          </Button>
        }
      />
    );
  }

  const events = data?.items ?? [];

  if (events.length === 0) {
    return (
      <EmptyState
        icon={RadioTower}
        title="No events yet"
        description="Hand raises and seating events will appear here as analytics publishes them."
      />
    );
  }

  return (
    <Panel className="p-0">
      <div className="flex items-center justify-between border-b border-ink-900/10 px-5 py-4">
        <div>
          <h2 className="text-lg font-black text-ink-900">Live events</h2>
          <p className="text-sm text-ink-500">Polling every 2 seconds</p>
        </div>
        <Badge tone="green">Live</Badge>
      </div>
      <div className="max-h-[680px] divide-y divide-ink-900/10 overflow-y-auto">
        {events.map((event) => {
          const zoneName =
            typeof event.payload.zone_name === "string"
              ? event.payload.zone_name
              : event.zone_id ?? "Unknown zone";

          return (
            <article
              key={event.id}
              className="grid gap-3 px-5 py-4 transition hover:bg-white/55 md:grid-cols-[1fr_auto]"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <EventTypeBadge eventType={event.event_type} />
                  <Badge tone="neutral">{titleCase(event.status)}</Badge>
                </div>
                <h3 className="mt-3 text-base font-black text-ink-900">
                  {zoneName}
                </h3>
                <p className="mt-1 text-sm leading-6 text-ink-500">
                  Camera {event.camera_id ?? "unknown"} with track{" "}
                  {event.track_id ?? "unknown"}
                </p>
              </div>
              <time className="text-sm font-bold text-ink-500">
                {formatDateTime(event.timestamp)}
              </time>
            </article>
          );
        })}
      </div>
    </Panel>
  );
}
