import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { createBackendApi, toRouteError } from "@/lib/api";
import { AUTH_COOKIE_NAME } from "@/lib/auth";
import type { SystemStatus } from "@/types/api";

interface RouteContext {
  params: {
    path?: string[];
  };
}

function tokenFromCookie(): string | null {
  return cookies().get(AUTH_COOKIE_NAME)?.value ?? null;
}

function unauthorized(): NextResponse {
  return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
}

function systemPath(context: RouteContext): string {
  const segments = context.params.path ?? [];
  return `/system/${segments.join("/")}`;
}

export async function GET(
  request: NextRequest,
  context: RouteContext
): Promise<NextResponse> {
  const token = tokenFromCookie();
  if (!token) {
    return unauthorized();
  }

  try {
    const query = request.nextUrl.searchParams.toString();
    const path = systemPath(context);
    const { data } = await createBackendApi(token).get<SystemStatus>(
      `${path}${query ? `?${query}` : ""}`
    );
    return NextResponse.json(data);
  } catch (error) {
    return toRouteError(error) as NextResponse;
  }
}

export async function POST(
  request: NextRequest,
  context: RouteContext
): Promise<NextResponse> {
  const token = tokenFromCookie();
  if (!token) {
    return unauthorized();
  }

  try {
    const payload = (await request.json()) as unknown;
    const { data } = await createBackendApi(token).post<SystemStatus>(
      systemPath(context),
      payload
    );
    return NextResponse.json(data);
  } catch (error) {
    return toRouteError(error) as NextResponse;
  }
}
