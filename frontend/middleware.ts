import { NextRequest, NextResponse } from "next/server";

/**
 * API reverse-proxy middleware.
 *
 * Proxies all /api/* requests to the backend, preserving the EXACT URL
 * (including trailing slashes) and following any redirects server-side so the
 * browser never sees a cross-origin 307 that drops the Authorization header.
 */

const BACKEND_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export async function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // Only proxy /api/* requests
  if (!pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  const targetUrl = `${BACKEND_URL}${pathname}${search}`;

  // Forward all headers, overriding host to match the backend
  const headers = new Headers(request.headers);
  headers.set("host", new URL(BACKEND_URL).host);

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "follow", // follow FastAPI 307 redirects server-side
  };

  // Forward body for non-GET/HEAD methods
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  try {
    const upstream = await fetch(targetUrl, init);

    // Strip hop-by-hop headers that shouldn't be forwarded
    const resHeaders = new Headers(upstream.headers);
    resHeaders.delete("transfer-encoding");

    return new NextResponse(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: resHeaders,
    });
  } catch {
    return NextResponse.json(
      { detail: "Backend unavailable" },
      { status: 502 },
    );
  }
}

export const config = {
  matcher: "/api/:path*",
};
