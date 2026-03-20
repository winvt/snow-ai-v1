import { NextRequest, NextResponse } from "next/server";

import { proxyJsonResponse, requestDelivery } from "@/lib/delivery-api";
import { isAdminAuthenticated } from "@/lib/session";

export async function GET(request: NextRequest) {
  if (!isAdminAuthenticated(request.cookies)) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  try {
    const upstream = await requestDelivery("/admin-api/system");
    return proxyJsonResponse(upstream);
  } catch {
    return NextResponse.json({ detail: "Failed to reach the delivery API." }, { status: 502 });
  }
}
