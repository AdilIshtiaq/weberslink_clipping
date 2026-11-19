import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// Keep every build step inside this folder. Without this, Next.js can pick a lockfile in a
// parent folder (for example the user profile on Windows) as the project root and scan it.
const projectRoot = process.cwd();

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  distDir: process.env.NEXT_BUILD_DIR || ".next",
  output: 'standalone',
  outputFileTracingRoot: projectRoot,
  // Keep canonical tags in the initial <head>, including for Googlebot.
  htmlLimitedBots: /.*/,
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default withNextIntl(nextConfig);
