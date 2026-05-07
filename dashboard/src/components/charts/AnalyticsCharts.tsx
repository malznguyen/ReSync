"use client";

import { Activity, BarChart3, LineChart as LineChartIcon, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import useSWR from "swr";

import { DateRangePicker } from "@/components/charts/DateRangePicker";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { getEvents, getVisits } from "@/lib/api";
import type { AnalyticsEvent, Visit } from "@/types/api";

interface HourlyVisitorsDatum {
  hour: string;
  visitors: number;
}

interface ZoneHandRaiseDatum {
  zone: string;
  count: number;
}

function toDateInput(value: Date): string {
  return value.toISOString().slice(0, 10);
}

function defaultStartDate(): string {
  const value = new Date();
  value.setDate(value.getDate() - 6);
  return toDateInput(value);
}

function hourLabel(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit"
  }).format(new Date(value));
}

function aggregateVisits(visits: Visit[]): HourlyVisitorsDatum[] {
  const counts = new Map<string, number>();
  visits.forEach((visit) => {
    const label = hourLabel(visit.entered_at);
    counts.set(label, (counts.get(label) ?? 0) + 1);
  });
  return Array.from(counts.entries()).map(([hour, visitors]) => ({
    hour,
    visitors
  }));
}

function zoneLabel(event: AnalyticsEvent): string {
  if (typeof event.payload.zone_name === "string") {
    return event.payload.zone_name;
  }
  return event.zone_id ?? "Unknown";
}

function aggregateHandRaises(events: AnalyticsEvent[]): ZoneHandRaiseDatum[] {
  const counts = new Map<string, number>();
  events
    .filter((event) => event.event_type === "hand_raise")
    .forEach((event) => {
      const label = zoneLabel(event);
      counts.set(label, (counts.get(label) ?? 0) + 1);
    });

  return Array.from(counts.entries())
    .map(([zone, count]) => ({ zone, count }))
    .sort((left, right) => right.count - left.count);
}

export function AnalyticsCharts(): JSX.Element {
  const [startDate, setStartDate] = useState(defaultStartDate);
  const [endDate, setEndDate] = useState(() => toDateInput(new Date()));

  const range = useMemo(
    () => ({
      startAt: startDate,
      endAt: endDate
    }),
    [endDate, startDate]
  );

  const visitsQuery = useSWR(["analytics-visits", range], () => getVisits(range));
  const eventsQuery = useSWR(["analytics-events", range], () => getEvents(range, 300));

  const hourlyVisitors = useMemo(
    () => aggregateVisits(visitsQuery.data?.items ?? []),
    [visitsQuery.data]
  );
  const handRaisesByZone = useMemo(
    () => aggregateHandRaises(eventsQuery.data?.items ?? []),
    [eventsQuery.data]
  );

  const isLoading = visitsQuery.isLoading || eventsQuery.isLoading;
  const hasError = Boolean(visitsQuery.error || eventsQuery.error);

  if (hasError) {
    return (
      <EmptyState
        icon={RefreshCw}
        title="Analytics unavailable"
        description="The dashboard could not load visits or event analytics."
        action={
          <Button
            onClick={() => {
              void visitsQuery.mutate();
              void eventsQuery.mutate();
            }}
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-5">
      <DateRangePicker
        startDate={startDate}
        endDate={endDate}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
      />

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel className="min-h-[420px]">
          <div className="mb-6 flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-lagoon-600">
                Visits
              </p>
              <h2 className="mt-2 text-xl font-black text-ink-900">
                Hourly visitors
              </h2>
            </div>
            <LineChartIcon className="h-5 w-5 text-ink-500" aria-hidden="true" />
          </div>
          {isLoading ? (
            <div className="h-72 animate-pulse rounded-lg bg-white/65" />
          ) : hourlyVisitors.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={hourlyVisitors}>
                  <CartesianGrid stroke="rgba(23, 26, 18, 0.08)" vertical={false} />
                  <XAxis
                    dataKey="hour"
                    tick={{ fontSize: 12, fill: "#686b58" }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 12, fill: "#686b58" }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 8,
                      border: "1px solid rgba(23, 26, 18, 0.1)"
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="visitors"
                    stroke="#1d6d68"
                    strokeWidth={3}
                    dot={{ r: 4, fill: "#1d6d68" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState
              icon={Activity}
              title="No visit data"
              description="Visitor counts will populate after analytics records visits."
            />
          )}
        </Panel>

        <Panel className="min-h-[420px]">
          <div className="mb-6 flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-copper-600">
                Service signals
              </p>
              <h2 className="mt-2 text-xl font-black text-ink-900">
                Hand raises by zone
              </h2>
            </div>
            <BarChart3 className="h-5 w-5 text-ink-500" aria-hidden="true" />
          </div>
          {isLoading ? (
            <div className="h-72 animate-pulse rounded-lg bg-white/65" />
          ) : handRaisesByZone.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={handRaisesByZone}>
                  <CartesianGrid stroke="rgba(23, 26, 18, 0.08)" vertical={false} />
                  <XAxis
                    dataKey="zone"
                    tick={{ fontSize: 12, fill: "#686b58" }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 12, fill: "#686b58" }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 8,
                      border: "1px solid rgba(23, 26, 18, 0.1)"
                    }}
                  />
                  <Bar dataKey="count" fill="#c77751" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState
              icon={Activity}
              title="No hand raises"
              description="Hand-raise counts will appear when events are dispatched."
            />
          )}
        </Panel>
      </div>
    </div>
  );
}
