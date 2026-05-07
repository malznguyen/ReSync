export const AUTH_COOKIE_NAME = "resync_token";

export function getHlsStreamUrl(cameraId: string): string {
  const baseUrl =
    process.env.NEXT_PUBLIC_HLS_BASE_URL?.replace(/\/$/, "") ??
    "http://localhost:8888";
  return `${baseUrl}/${cameraId}/index.m3u8`;
}
