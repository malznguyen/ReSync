import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth";
import { createBackendApi, toRouteError } from "@/lib/api";
import type { Zone, ZoneCreate } from "@/types/api";

function tokenFromCookie(): string | null {
  return cookies().get(AUTH_COOKIE_NAME)?.value ?? null;
}

function unauthorized(): NextResponse {
  return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const token = tokenFromCookie();
  if (!token) {
    return unauthorized();
  }

  try {
    const query = request.nextUrl.searchParams.toString();
    const path = `/zones${query ? `?${query}` : ""}`;
    const { data } = await createBackendApi(token).get<Zone[]>(path);
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
    const payload = (await request.json()) as ZoneCreate;
    const { data } = await createBackendApi(token).post<Zone>("/zones", payload);
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    return toRouteError(error) as NextResponse;
  }
}
