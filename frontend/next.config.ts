import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  distDir: process.env.NEXT_BUILD_DIR || ".next",
  output: 'standalone',
  // Keep canonical tags in the initial <head>, including for Googlebot.
  htmlLimitedBots: /.*/,
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default withNextIntl(nextConfig);
