import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth";
import { createBackendApi, toRouteError } from "@/lib/api";
import type { TrackOutput } from "@/types/api";

interface RouteContext {
  params: {
    camera_id: string;
  };
}

export async function GET(
  _request: Request,
  { params }: RouteContext
): Promise<NextResponse> {
  const token = cookies().get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  try {
    const { data } = await createBackendApi(token).get<TrackOutput>(
      `/cameras/${params.camera_id}/tracks/latest`
    );
    return NextResponse.json(data);
  } catch (error) {
    return toRouteError(error) as NextResponse;
  }
}
