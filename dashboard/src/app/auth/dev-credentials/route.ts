import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(): Promise<NextResponse> {
  if (process.env.DASHBOARD_DEV_LOGIN_ENABLED !== "true") {
    return NextResponse.json(
      { detail: "Local admin autofill is disabled" },
      { status: 404 }
    );
  }

  const username =
    process.env.DASHBOARD_DEV_USERNAME ?? process.env.API_ADMIN_USERNAME;
  const password =
    process.env.DASHBOARD_DEV_PASSWORD ?? process.env.API_ADMIN_PASSWORD;

  if (!username || !password) {
    return NextResponse.json(
      { detail: "Local admin credentials are not configured" },
      { status: 404 }
    );
  }

  return NextResponse.json(
    { username, password },
    {
      headers: {
        "Cache-Control": "no-store"
      }
    }
  );
}
