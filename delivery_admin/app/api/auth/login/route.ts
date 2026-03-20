import { timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

import { getAdminPassword } from "@/lib/config";
import { createSessionToken, setSessionCookie } from "@/lib/session";

function safeEqual(left: string, right: string): boolean {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);
  if (leftBuffer.length !== rightBuffer.length) {
    return false;
  }
  return timingSafeEqual(leftBuffer, rightBuffer);
}

export async function POST(request: NextRequest) {
  let payload: { password?: string };
  try {
    payload = (await request.json()) as { password?: string };
  } catch {
    return NextResponse.json({ detail: "Invalid request payload." }, { status: 400 });
  }

  let configuredPassword: string;
  try {
    configuredPassword = getAdminPassword();
  } catch {
    return NextResponse.json({ detail: "ADMIN_PASSWORD is not configured." }, { status: 503 });
  }
  const submittedPassword = (payload.password || "").trim();
  if (!submittedPassword || !safeEqual(submittedPassword, configuredPassword)) {
    return NextResponse.json({ detail: "Invalid password." }, { status: 401 });
  }

  let sessionToken: string;
  try {
    sessionToken = createSessionToken();
  } catch {
    return NextResponse.json({ detail: "ADMIN_SESSION_SECRET is not configured." }, { status: 503 });
  }
  const response = NextResponse.json({ authenticated: true });
  setSessionCookie(response, sessionToken);
  return response;
}
