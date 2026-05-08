import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function getRtspStreamPath(rtspUrl: string): string {
  const value = rtspUrl.trim();
  if (!value) {
    return "";
  }

  try {
    const pathSegments = new URL(value).pathname.split("/").filter(Boolean);
    return pathSegments[pathSegments.length - 1] ?? "";
  } catch {
    const [withoutQuery] = value.split(/[?#]/);
    const segments = withoutQuery.replace(/\/+$/, "").split("/").filter(Boolean);
    return segments[segments.length - 1] ?? "";
  }
}

export function getHlsStreamUrl(rtspUrl: string): string {
  const baseUrl =
    process.env.NEXT_PUBLIC_HLS_BASE_URL?.replace(/\/$/, "") ??
    "http://localhost:8888";
  const streamPath = getRtspStreamPath(rtspUrl);
  return `${baseUrl}/${streamPath}/index.m3u8`;
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

export function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function normalizeStatus(status: string): "online" | "offline" | "idle" {
  const value = status.toLowerCase();
  if (value === "active" || value === "online") {
    return "online";
  }
  if (value === "offline" || value === "inactive") {
    return "offline";
  }
  return "idle";
}

export function titleCase(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
