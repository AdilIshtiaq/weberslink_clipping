export const SITE_NAME = "WeberslinkClip";
export const COMPANY_NAME = "WebersLink";
export const DEFAULT_SITE_URL = "https://clip.weberslink.org";
export const HOSTED_APP_URL = DEFAULT_SITE_URL;
export function getSiteUrl() {
  try {
    return new URL(process.env.NEXT_PUBLIC_APP_URL || DEFAULT_SITE_URL).origin;
  } catch {
    return DEFAULT_SITE_URL;
  }
}
