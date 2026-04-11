import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Prevent Next.js from 308-redirecting trailing-slash URLs.
  // FastAPI expects trailing slashes on some routes; without this flag Next.js
  // strips the slash before middleware sees the request.
  skipTrailingSlashRedirect: true,
  async headers() {
    return [
      {
        // HTML pages: never cache so browsers always get the latest chunk manifest after a deploy
        source: "/((?!_next/static|_next/image|favicon.ico).*)",
        headers: [
          {
            key: "Cache-Control",
            value: "no-cache, no-store, must-revalidate",
          },
        ],
      },
      {
        // Static assets (JS/CSS with content-hash filenames): cache aggressively
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
