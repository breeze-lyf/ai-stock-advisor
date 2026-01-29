import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  typescript: {
    ignoreBuildErrors: true,
  },
  // 如果 eslint 属性报错，我们直接使用这种通配方式
  experimental: {
    // 某些版本可能需要这个
  }
};

export default nextConfig;
