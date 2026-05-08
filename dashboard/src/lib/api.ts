import axios, { AxiosError, type AxiosInstance } from "axios";

import type {
  AnalyticsEvent,
  Camera,
  CameraCreate,
  DateRange,
  LoginCredentials,
  PaginatedResponse,
  TrackOutput,
  Visit,
  Zone,
  ZoneCreate
} from "@/types/api";

interface ApiErrorPayload {
  detail?: string;
}

interface AuthTokenResponse {
  access_token: string;
  token_type: string;
}

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly status?: number
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

const dashboardApi = axios.create({
  withCredentials: true,
  timeout: 15000
});

export function createBackendApi(token: string): AxiosInstance {
  return axios.create({
    baseURL: process.env.API_BASE_URL ?? "http://localhost:8000",
    timeout: 15000,
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiErrorPayload>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed";
}

export function toRouteError(error: unknown): Response {
  if (axios.isAxiosError<ApiErrorPayload>(error)) {
    const status = error.response?.status ?? 502;
    const message = getApiErrorMessage(error);
    return Response.json({ detail: message }, { status });
  }
  return Response.json({ detail: "Unexpected server error" }, { status: 500 });
}

export async function requestAuthToken(
  username: string,
  password: string
): Promise<AuthTokenResponse> {
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);

  const { data } = await axios.post<AuthTokenResponse>(
    `${process.env.API_BASE_URL ?? "http://localhost:8000"}/auth/token`,
    body,
    {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      },
      timeout: 15000
    }
  );

  return data;
}

async function unwrap<T>(request: Promise<{ data: T }>): Promise<T> {
  try {
    const response = await request;
    return response.data;
  } catch (error) {
    const status = axios.isAxiosError(error) ? error.response?.status : undefined;
    throw new ApiClientError(getApiErrorMessage(error), status);
  }
}

function withDateRange(params: URLSearchParams, range?: DateRange): void {
  if (range?.startAt) {
    params.set("start_at", new Date(range.startAt).toISOString());
  }
  if (range?.endAt) {
    params.set("end_at", new Date(range.endAt).toISOString());
  }
}

export async function login(credentials: LoginCredentials): Promise<void> {
  const body = new URLSearchParams();
  body.set("username", credentials.username);
  body.set("password", credentials.password);

  await unwrap(
    dashboardApi.post<{ ok: boolean }>("/auth/token", body, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      }
    })
  );
}

export async function getDevCredentials(): Promise<LoginCredentials> {
  return unwrap(dashboardApi.get<LoginCredentials>("/auth/dev-credentials"));
}

export async function logout(): Promise<void> {
  await unwrap(dashboardApi.post<{ ok: boolean }>("/auth/logout"));
}

export async function getCameras(): Promise<Camera[]> {
  return unwrap(dashboardApi.get<Camera[]>("/api/cameras"));
}

export async function createCamera(payload: CameraCreate): Promise<Camera> {
  return unwrap(dashboardApi.post<Camera>("/api/cameras", payload));
}

export async function getCameraTracks(cameraId: string): Promise<TrackOutput> {
  return unwrap(
    dashboardApi.get<TrackOutput>(`/api/cameras/${cameraId}/tracks`)
  );
}

export async function getZones(cameraId?: string): Promise<Zone[]> {
  const params = new URLSearchParams();
  if (cameraId) {
    params.set("camera_id", cameraId);
  }
  const query = params.toString();
  return unwrap(dashboardApi.get<Zone[]>(`/api/zones${query ? `?${query}` : ""}`));
}

export async function createZone(payload: ZoneCreate): Promise<Zone> {
  return unwrap(dashboardApi.post<Zone>("/api/zones", payload));
}

export async function getEvents(
  range?: DateRange,
  limit = 80
): Promise<PaginatedResponse<AnalyticsEvent>> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  withDateRange(params, range);
  return unwrap(
    dashboardApi.get<PaginatedResponse<AnalyticsEvent>>(
      `/api/analytics/events?${params.toString()}`
    )
  );
}

export async function getVisits(
  range?: DateRange,
  limit = 200
): Promise<PaginatedResponse<Visit>> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  withDateRange(params, range);
  return unwrap(
    dashboardApi.get<PaginatedResponse<Visit>>(
      `/api/analytics/visits?${params.toString()}`
    )
  );
}

export function getRouteDetail(response: Response): string {
  return response.statusText || "Request failed";
}

export type { AxiosError };
