import { NextRequest, NextResponse } from "next/server";

import { proxyJsonResponse, requestDelivery } from "@/lib/delivery-api";
import { isAdminAuthenticated } from "@/lib/session";

type RouteContext = {
  params: {
    lineUserId: string;
  };
};

export async function PUT(request: NextRequest, { params }: RouteContext) {
  if (!isAdminAuthenticated(request.cookies)) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const body = await request.text();
  try {
    const upstream = await requestDelivery(
      `/admin-api/access/users/${encodeURIComponent(params.lineUserId)}/locations`,
      {
        method: "PUT",
        body,
        headers: {
          "content-type": "application/json",
        },
      }
    );
    return proxyJsonResponse(upstream);
  } catch {
    return NextResponse.json({ detail: "Failed to reach the delivery API." }, { status: 502 });
  }
}
