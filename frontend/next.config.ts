import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 로컬 개발 시에만 rewrites 프록시 활성화
  // Railway 배포 시에는 NEXT_PUBLIC_BACKEND_URL로 직접 호출
  async rewrites() {
    if (process.env.NEXT_PUBLIC_BACKEND_URL) {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
  // Disable network interface detection to avoid errors
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
};

export default nextConfig;
