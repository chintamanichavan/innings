import type { NextConfig } from "next";

// The Python server that owns the data and the models. The browser never talks to it
// directly: every /api request comes here first and is passed on.
const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  output: "standalone",
  allowedDevOrigins: ["127.0.0.1"], // the dev server is opened by address, not by name
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default config;
