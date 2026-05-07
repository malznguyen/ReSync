import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth";
import { createBackendApi, toRouteError } from "@/lib/api";
import type { Camera, CameraCreate } from "@/types/api";

function tokenFromCookie(): string | null {
  return cookies().get(AUTH_COOKIE_NAME)?.value ?? null;
}

function unauthorized(): NextResponse {
  return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
}

export async function GET(): Promise<NextResponse> {
  const token = tokenFromCookie();
  if (!token) {
    return unauthorized();
  }

  try {
    const { data } = await createBackendApi(token).get<Camera[]>("/cameras");
    return NextResponse.json(data);
  } catch (error) {
    return toRouteError(error) as NextResponse;
  }
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const token = tokenFromCookie();
  if (!token) {
    return unauthorized();
  }

  try {
    const payload = (await request.json()) as CameraCreate;
    const { data } = await createBackendApi(token).post<Camera>(
      "/cameras",
      payload
    );
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    return toRouteError(error) as NextResponse;
  }
}
