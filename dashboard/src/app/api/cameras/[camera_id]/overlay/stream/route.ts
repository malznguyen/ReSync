import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth";

interface RouteContext {
  params: {
    camera_id: string;
  };
}

export async function GET(
  _request: Request,
  { params }: RouteContext
): Promise<Response> {
  const token = cookies().get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(
    `${apiBaseUrl}/cameras/${params.camera_id}/overlay/stream`,
    {
      headers: {
        Authorization: `Bearer ${token}`
      },
      cache: "no-store"
    }
  );

  if (!response.ok || response.body === null) {
    const detail = await response.text();
    return NextResponse.json(
      { detail: detail || "Overlay stream unavailable" },
      { status: response.status || 502 }
    );
  }

  return new Response(response.body, {
    status: response.status,
    headers: {
      "Content-Type":
        response.headers.get("content-type") ??
        "multipart/x-mixed-replace; boundary=frame",
      "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
      Pragma: "no-cache"
    }
  });
}
