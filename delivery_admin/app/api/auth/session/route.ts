import { NextRequest, NextResponse } from "next/server";

import { isAdminAuthenticated } from "@/lib/session";

export async function GET(request: NextRequest) {
  return NextResponse.json({ authenticated: isAdminAuthenticated(request.cookies) });
}
