import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // standalone output keeps the Docker image small (frontend/Dockerfile relies on it)
  output: "standalone",
  // keep the workspace root unambiguous (repo root sits above the frontend folder)
  turbopack: { root: __dirname },
};

export default nextConfig;
