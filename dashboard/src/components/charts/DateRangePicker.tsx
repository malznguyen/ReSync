"use client";

import { CalendarDays } from "lucide-react";

import { Input } from "@/components/ui/Input";

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onStartDateChange: (value: string) => void;
  onEndDateChange: (value: string) => void;
}

export function DateRangePicker({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange
}: DateRangePickerProps): JSX.Element {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-ink-900/10 bg-white/65 p-3 sm:flex-row sm:items-end">
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-lagoon-100 text-lagoon-600">
        <CalendarDays className="h-5 w-5" aria-hidden="true" />
      </div>
      <Input
        label="Start date"
        name="start-date"
        type="date"
        value={startDate}
        onChange={(event) => onStartDateChange(event.target.value)}
      />
      <Input
        label="End date"
        name="end-date"
        type="date"
        value={endDate}
        onChange={(event) => onEndDateChange(event.target.value)}
      />
    </div>
  );
}
