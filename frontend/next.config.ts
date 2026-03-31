import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  typescript: {
    ignoreBuildErrors: true,
  },
  // Prevent Next.js from 308-redirecting trailing-slash URLs.
  // FastAPI expects trailing slashes on some routes; without this flag Next.js
  // strips the slash before middleware sees the request.
  skipTrailingSlashRedirect: true,
};

export default nextConfig;
