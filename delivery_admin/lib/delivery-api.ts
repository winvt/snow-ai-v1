import "server-only";

import { getAdminInternalApiToken, getDeliveryApiBaseUrl } from "./config";

type DeliveryRequestOptions = {
  method?: string;
  search?: string;
  headers?: HeadersInit;
  body?: BodyInit | null;
};

function buildUpstreamUrl(path: string, search?: string): string {
  const baseUrl = getDeliveryApiBaseUrl();
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${baseUrl}${normalizedPath}`);
  if (search) {
    url.search = search;
  }
  return url.toString();
}

export async function requestDelivery(path: string, options: DeliveryRequestOptions = {}): Promise<Response> {
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${getAdminInternalApiToken()}`);
  return fetch(buildUpstreamUrl(path, options.search), {
    method: options.method ?? "GET",
    headers,
    body: options.body,
    cache: "no-store",
  });
}

export async function proxyJsonResponse(response: Response): Promise<Response> {
  const text = await response.text();
  return new Response(text || "{}", {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") || "application/json",
    },
  });
}

export async function proxyBinaryResponse(response: Response): Promise<Response> {
  const payload = await response.arrayBuffer();
  const headers = new Headers();
  const passThroughHeaders = [
    "content-type",
    "content-length",
    "cache-control",
    "etag",
    "last-modified",
    "content-disposition",
  ];
  passThroughHeaders.forEach((name) => {
    const value = response.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  });
  return new Response(payload, {
    status: response.status,
    headers,
  });
}
