import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

// The Docker image runs Next.js's "standalone" server (the Dockerfile sets NEXT_STANDALONE=true).
// Local runs use plain `next start`, which does not need that output mode.
const standalone = process.env.NEXT_STANDALONE === "true";

const nextConfig: NextConfig = {
  distDir: process.env.NEXT_BUILD_DIR || ".next",
  ...(standalone ? { output: "standalone" as const, outputFileTracingRoot: process.cwd() } : {}),
  // Keep canonical tags in the initial <head>, including for Googlebot.
  htmlLimitedBots: /.*/,
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default withNextIntl(nextConfig);
