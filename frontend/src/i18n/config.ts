export const locales = ["en"] as const;

export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

export const LOCALE_COOKIE = "NEXT_LOCALE";

/** Top-level message files under `frontend/messages/<locale>/`. */
export const NAMESPACES = [
  "common",
  "metadata",
  "shell",
  "auth",
  "settings",
  "billing",
  "home",
  "library",
  "task",
  "editor",
  "social",
  "analytics",
  "marketing",
  "admin",
  "share",
  "legal",
] as const;

export type Namespace = (typeof NAMESPACES)[number];

export function isLocale(value: string | null | undefined): value is Locale {
  return !!value && (locales as readonly string[]).includes(value);
}

/** BCP 47 tag used for `lang`, dates, and `Intl` formatters. */
export function intlLocale(locale: string): string {
  return locale;
}

/** The product ships in English only. */
export function negotiateLocale(): Locale {
  return defaultLocale;
}
