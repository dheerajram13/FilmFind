import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  allowedDevOrigins: [
    "localhost",
    "127.0.0.1",
    "frontend.filmfind.orb.local",
  ],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "image.tmdb.org",
        pathname: "/t/p/**",
      },
      {
        // Supabase Storage CDN
        protocol: "https",
        hostname: "hmfqdofdkzpphmjxdqgl.supabase.co",
        pathname: "/storage/v1/object/public/**",
      },
    ],
    // Disable optimization for TMDB images to avoid timeout issues in Docker
    unoptimized: true,
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

export default nextConfig;
