import type { NextConfig } from "next";
import { PHASE_PRODUCTION_BUILD } from "next/constants";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
    ] }];
  },
};

export default function configure(phase: string): NextConfig {
  if (phase === PHASE_PRODUCTION_BUILD) {
    const api = process.env.NEXT_PUBLIC_API_URL;
    if (!api) throw new Error("Set NEXT_PUBLIC_API_URL before building the frontend");
    const url = new URL(api);
    if (!["http:", "https:"].includes(url.protocol)) throw new Error("NEXT_PUBLIC_API_URL must be an HTTP(S) origin");
    if (url.pathname !== "/" || url.search || url.hash || url.username || url.password) {
      throw new Error("NEXT_PUBLIC_API_URL must be an origin without a path, credentials or query");
    }
  }
  return nextConfig;
}
