import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth";
import { createBackendApi, toRouteError } from "@/lib/api";
import type { AnalyticsEvent, PaginatedResponse } from "@/types/api";

function tokenFromCookie(): string | null {
  return cookies().get(AUTH_COOKIE_NAME)?.value ?? null;
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const token = tokenFromCookie();
  if (!token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const query = request.nextUrl.searchParams.toString();
    const path = `/analytics/events${query ? `?${query}` : ""}`;
    const { data } =
      await createBackendApi(token).get<PaginatedResponse<AnalyticsEvent>>(path);
    return NextResponse.json(data);
  } catch (error) {
    return toRouteError(error) as NextResponse;
  }
}
