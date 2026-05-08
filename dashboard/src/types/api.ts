export type CameraStatus = "active" | "inactive" | "offline" | "online" | string;

export type Point = [number, number];

export interface Camera {
  id: string;
  name: string;
  rtsp_url: string;
  status: CameraStatus;
  created_at: string;
}

export interface CameraCreate {
  name: string;
  rtsp_url: string;
  status: string;
}

export type Keypoint = [number, number, number];

export type BoundingBox = [number, number, number, number];

export interface Track {
  track_id: string;
  bbox: BoundingBox;
  keypoints: Keypoint[];
  confidence: number;
  customer_id: string | null;
}

export interface TrackOutput {
  frame_id: string;
  timestamp: number | null;
  camera_id: string;
  tracks: Track[];
}

export interface Zone {
  id: string;
  camera_id: string;
  name: string;
  polygon: Point[];
  active: boolean;
}

export interface ZoneCreate {
  camera_id: string;
  name: string;
  polygon: Point[];
  active: boolean;
}

export interface AnalyticsEvent {
  id: string;
  event_type: string;
  customer_id: string | null;
  zone_id: string | null;
  camera_id: string | null;
  track_id: string | null;
  timestamp: string;
  status: string;
  payload: Record<string, unknown>;
  webhook_response: Record<string, unknown> | null;
}

export interface Visit {
  id: string;
  customer_id: string | null;
  zone_id: string | null;
  camera_id: string | null;
  entered_at: string;
  left_at: string | null;
}

export interface PaginatedResponse<T> {
  limit: number;
  offset: number;
  items: T[];
}

export interface DateRange {
  startAt?: string;
  endAt?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface MockCameraStatus {
  enabled: boolean;
  running: boolean;
  available: boolean;
  source_path: string;
  rtsp_url: string;
  detail: string | null;
}

export interface SystemStatus {
  inference_enabled: boolean;
  reid_enabled: boolean;
  mock_camera: MockCameraStatus;
}
