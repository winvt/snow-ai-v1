import { createHmac, timingSafeEqual } from "node:crypto";
import { redirect } from "next/navigation";
import { NextResponse } from "next/server";

import { getAdminSessionSecret } from "./config";

const SESSION_COOKIE_NAME = "delivery_admin_session";
const SESSION_TTL_SECONDS = 60 * 60 * 24;

type CookieStoreLike = {
  get(name: string): { value: string } | undefined;
};

type SessionPayload = {
  sub: "admin";
  exp: number;
};

function sign(value: string): string {
  return createHmac("sha256", getAdminSessionSecret()).update(value).digest("base64url");
}

function safeEqual(left: string, right: string): boolean {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);
  if (leftBuffer.length !== rightBuffer.length) {
    return false;
  }
  return timingSafeEqual(leftBuffer, rightBuffer);
}

export function createSessionToken(): string {
  const payload: SessionPayload = {
    sub: "admin",
    exp: Date.now() + SESSION_TTL_SECONDS * 1000,
  };
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${encodedPayload}.${sign(encodedPayload)}`;
}

export function verifySessionToken(token: string | undefined | null): SessionPayload | null {
  if (!token) {
    return null;
  }
  const [encodedPayload, encodedSignature] = token.split(".");
  if (!encodedPayload || !encodedSignature) {
    return null;
  }
  let expectedSignature: string;
  try {
    expectedSignature = sign(encodedPayload);
  } catch {
    return null;
  }
  if (!safeEqual(encodedSignature, expectedSignature)) {
    return null;
  }

  try {
    const payload = JSON.parse(Buffer.from(encodedPayload, "base64url").toString("utf8")) as SessionPayload;
    if (payload.sub !== "admin" || !payload.exp || payload.exp < Date.now()) {
      return null;
    }
    return payload;
  } catch {
    return null;
  }
}

export function isAdminAuthenticated(cookieStore: CookieStoreLike): boolean {
  return Boolean(verifySessionToken(cookieStore.get(SESSION_COOKIE_NAME)?.value));
}

export function requireAdminSession(cookieStore: CookieStoreLike): void {
  if (!isAdminAuthenticated(cookieStore)) {
    redirect("/login");
  }
}

export function redirectIfAuthenticated(cookieStore: CookieStoreLike): void {
  if (isAdminAuthenticated(cookieStore)) {
    redirect("/reports");
  }
}

export function setSessionCookie(response: NextResponse, token: string): void {
  response.cookies.set({
    name: SESSION_COOKIE_NAME,
    value: token,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });
}

export function clearSessionCookie(response: NextResponse): void {
  response.cookies.set({
    name: SESSION_COOKIE_NAME,
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
}
