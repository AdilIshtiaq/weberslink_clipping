"use client";

import Image from "next/image";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { COMPANY_NAME } from "@/lib/site";

const linkClassName = "hover:text-foreground transition-colors";

/** Footer for the landing page and legal pages. */
export function SiteFooter() {
  const t = useTranslations("marketing");

  return (
    <footer className="border-t px-6 py-12">
      <div className="mx-auto grid max-w-6xl gap-10 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <Link href="/" className="flex items-center gap-2">
            <Image src="/logo.png" alt="WeberslinkClip" width={32} height={32} className="rounded-md" />
            <span className="text-sm font-semibold" style={{ fontFamily: "var(--font-archivo), system-ui" }}>
              WeberslinkClip
            </span>
          </Link>
          <p className="mt-3 max-w-xs text-xs leading-6 text-muted-foreground">{t("footer.tagline")}</p>
          <p className="mt-2 text-xs leading-6 text-muted-foreground">{t("footer.operator", { company: COMPANY_NAME })}</p>
          <p className="mt-4 text-xs text-muted-foreground">
            &copy; {new Date().getFullYear()} {COMPANY_NAME}
          </p>
        </div>
        <nav aria-label={t("footer.product")}>
          <p className="text-sm font-medium">{t("footer.product")}</p>
          <ul className="mt-4 space-y-2.5 text-xs text-muted-foreground">
            <li><Link href="/#how-it-works" className={linkClassName}>{t("nav.howItWorks")}</Link></li>
            <li><Link href="/#features" className={linkClassName}>{t("nav.features")}</Link></li>
            <li><Link href="/#pricing" className={linkClassName}>{t("nav.pricing")}</Link></li>
            <li><Link href="/sign-up" className={linkClassName}>{t("nav.getStarted")}</Link></li>
          </ul>
        </nav>
        <nav aria-label={t("footer.company")}>
          <p className="text-sm font-medium">{t("footer.company")}</p>
          <ul className="mt-4 space-y-2.5 text-xs text-muted-foreground">
            <li><a href="https://weberslink.org" target="_blank" rel="noopener noreferrer" className={linkClassName}>weberslink.org</a></li>
            <li><a href="mailto:hassan@weberslink.org" className={linkClassName}>{t("footer.contact")}</a></li>
            <li><Link href="/privacy" className={linkClassName}>Privacy</Link></li>
            <li><Link href="/terms" className={linkClassName}>Terms</Link></li>
          </ul>
        </nav>
      </div>
    </footer>
  );
}
