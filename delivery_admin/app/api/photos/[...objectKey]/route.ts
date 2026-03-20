import { NextRequest, NextResponse } from "next/server";

import { proxyBinaryResponse, requestDelivery } from "../../../../lib/delivery-api";
import { isAdminAuthenticated } from "../../../../lib/session";

type RouteContext = {
  params: {
    objectKey: string[];
  };
};

export async function GET(request: NextRequest, { params }: RouteContext) {
  if (!isAdminAuthenticated(request.cookies)) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const encodedKey = params.objectKey.map((segment) => encodeURIComponent(segment)).join("/");
  try {
    const upstream = await requestDelivery(`/admin-api/photos/${encodedKey}`, {
      search: request.nextUrl.searchParams.toString(),
    });
    return proxyBinaryResponse(upstream);
  } catch {
    return NextResponse.json({ detail: "Failed to reach the delivery API." }, { status: 502 });
  }
}
