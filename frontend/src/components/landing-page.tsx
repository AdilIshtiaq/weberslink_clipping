"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import Image from "next/image";
import {
  ArrowRight,
  Captions,
  Check,
  Crop,
  Download,
  Menu,
  Scissors,
  Sparkles,
  Type,
  X,
  type LucideIcon,
} from "lucide-react";

import { Reveal, SectionHeading } from "@/components/landing/reveal";
import { SiteFooter } from "@/components/marketing/site-footer";
import { Button } from "@/components/ui/button";
import { VIDEO_SOURCE_LABELS, VideoSourceIcon, type VideoSourceKind } from "@/components/video-source-icon";
import { getEarlyBirdPlan, getPublicBillingPlans, planPrice } from "@/lib/billing-plans";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "#how-it-works", key: "howItWorks" },
  { href: "#features", key: "features" },
  { href: "#pricing", key: "pricing" },
] as const;

const SOURCES: VideoSourceKind[] = ["youtube", "twitch", "kick", "upload"];

const FEATURES: { key: string; icon: LucideIcon }[] = [
  { key: "find", icon: Sparkles },
  { key: "crop", icon: Crop },
  { key: "captions", icon: Captions },
  { key: "hook", icon: Type },
  { key: "editor", icon: Scissors },
  { key: "export", icon: Download },
];

function formatHours(minutes: number) {
  const hours = minutes / 60;
  return Number.isInteger(hours) ? `${hours} hours` : `${hours.toFixed(1)} hours`;
}

export default function LandingPage() {
  const t = useTranslations("marketing");
  const [scrolled, setScrolled] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const earlyBird = getEarlyBirdPlan();
  const paidPlans = getPublicBillingPlans();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 24);
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* ─── NAV ─── */}
      <header className="fixed inset-x-0 top-0 z-50 px-3 pt-3">
        <nav
          className={cn(
            "mx-auto flex h-14 max-w-6xl items-center justify-between rounded-full border pl-4 pr-2 transition-all duration-300",
            scrolled || mobileNavOpen
              ? "border-border bg-background/80 shadow-[0_8px_30px_-12px_oklch(0.2_0.01_50/0.25)] backdrop-blur-xl"
              : "border-transparent bg-transparent",
          )}
        >
          <Link href="/" className="flex items-center gap-2">
            <Image src="/logo.png" alt="WeberslinkClip" width={32} height={32} className="rounded-md" />
            <span className="font-display text-[17px] font-bold tracking-tight">WeberslinkClip</span>
          </Link>

          <div className="hidden items-center gap-1 md:flex">
            {NAV_LINKS.map(({ href, key }) => (
              <a
                key={key}
                href={href}
                className="whitespace-nowrap rounded-full px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                {t(`nav.${key}`)}
              </a>
            ))}
          </div>

          <div className="hidden items-center gap-1 md:flex">
            <Button asChild variant="ghost" size="sm" className="rounded-full">
              <Link href="/sign-in">{t("nav.signIn")}</Link>
            </Button>
            <Button asChild size="sm" className="rounded-full px-4">
              <Link href="/sign-up">{t("nav.getStarted")}</Link>
            </Button>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileNavOpen((open) => !open)}
            className="rounded-full md:hidden"
            aria-label={t("nav.toggleMenu")}
            aria-expanded={mobileNavOpen}
          >
            {mobileNavOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </Button>
        </nav>

        {mobileNavOpen && (
          <div className="animate-rise mx-auto mt-2 max-w-6xl rounded-3xl border bg-background/95 p-3 shadow-lg backdrop-blur-xl md:hidden">
            {NAV_LINKS.map(({ href, key }) => (
              <a
                key={key}
                href={href}
                onClick={() => setMobileNavOpen(false)}
                className="block rounded-2xl px-4 py-3 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                {t(`nav.${key}`)}
              </a>
            ))}
            <div className="mt-2 grid grid-cols-2 gap-2 border-t pt-3">
              <Button asChild variant="outline" className="rounded-full">
                <Link href="/sign-in" onClick={() => setMobileNavOpen(false)}>{t("nav.signIn")}</Link>
              </Button>
              <Button asChild className="rounded-full">
                <Link href="/sign-up" onClick={() => setMobileNavOpen(false)}>{t("nav.getStarted")}</Link>
              </Button>
            </div>
          </div>
        )}
      </header>

      {/* ─── HERO ─── */}
      <section className="relative overflow-hidden pb-20 pt-32 md:pb-28 md:pt-40">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.035] [background-image:radial-gradient(circle_at_1px_1px,currentColor_1px,transparent_0)] [background-size:28px_28px] [mask-image:linear-gradient(to_bottom,black,transparent_70%)]"
        />
        <div className="relative mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-4xl text-center">
            {earlyBird.enabled && (
              <p
                className="mb-8 inline-flex items-center rounded-full border border-brand/30 bg-brand-soft px-4 py-1.5 font-mono text-xs uppercase tracking-[0.14em] text-brand"
                style={{ animation: "landing-fade-in-up 0.7s ease-out both" }}
              >
                {t("hero.badge")}
              </p>
            )}

            <h1
              className="font-display text-5xl font-extrabold leading-[1.02] tracking-tight text-balance sm:text-7xl md:text-8xl"
              style={{ animation: "landing-fade-in-up 0.7s ease-out 0.08s both" }}
            >
              {t("hero.titleLine1")}
              <br />
              <span className="text-brand">{t("hero.titleLine2")}</span>
            </h1>

            <p
              className="mx-auto mt-8 max-w-2xl text-lg leading-relaxed text-muted-foreground text-pretty"
              style={{ animation: "landing-fade-in-up 0.7s ease-out 0.16s both" }}
            >
              {t("hero.body")}
            </p>

            <div
              className="mt-10 flex flex-wrap items-center justify-center gap-3"
              style={{ animation: "landing-fade-in-up 0.7s ease-out 0.24s both" }}
            >
              <Button asChild size="lg" className="h-12 rounded-full px-7 text-sm">
                <Link href="/sign-up">
                  {t("hero.startClipping")}
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="h-12 rounded-full px-7 text-sm">
                <a href="#pricing">{t("hero.seePricing")}</a>
              </Button>
            </div>
            {earlyBird.enabled && <p className="mt-4 text-xs text-muted-foreground">{t("hero.note")}</p>}

            <div className="mt-14 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 text-sm text-muted-foreground">
              <span className="font-mono text-xs uppercase tracking-[0.14em]">{t("hero.sources.label")}</span>
              {SOURCES.map((kind) => (
                <span key={kind} className="inline-flex items-center gap-2">
                  <VideoSourceIcon source={kind} aria-hidden className="size-5" />
                  {kind === "upload" ? t("hero.sources.upload") : VIDEO_SOURCE_LABELS[kind]}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS ─── */}
      <section id="how-it-works" className="scroll-mt-24 border-y bg-canvas py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <SectionHeading eyebrow={t("steps.eyebrow")} title={t("steps.title")} />
          <div className="mt-14 grid gap-5 md:grid-cols-3">
            {(["drop", "gold", "export"] as const).map((step, index) => (
              <Reveal key={step} delay={index * 0.08} className="h-full">
                <div className="h-full rounded-3xl border bg-card p-7">
                  <span className="font-mono text-xs text-brand">0{index + 1}</span>
                  <h3 className="mt-3 font-display text-xl font-bold tracking-tight">{t(`steps.items.${step}.title`)}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{t(`steps.items.${step}.description`)}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FEATURES ─── */}
      <section id="features" className="scroll-mt-24 py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <SectionHeading eyebrow={t("features.eyebrow")} title={t("features.title")} body={t("features.body")} />
          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ key, icon: Icon }, index) => (
              <Reveal key={key} delay={(index % 3) * 0.06} className="h-full">
                <div className="h-full rounded-3xl border bg-card p-7">
                  <span className="flex size-10 items-center justify-center rounded-full bg-brand-soft text-brand">
                    <Icon className="size-5" aria-hidden />
                  </span>
                  <h3 className="mt-5 font-display text-lg font-bold tracking-tight">{t(`features.items.${key}.title`)}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{t(`features.items.${key}.description`)}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ─── PRICING ─── */}
      <section id="pricing" className="scroll-mt-24 border-t bg-canvas py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <SectionHeading eyebrow={t("pricing.eyebrow")} title={t("pricing.title")} body={t("pricing.body")} />
          <div className={cn("mt-14 grid gap-5", earlyBird.enabled ? "lg:grid-cols-3" : "mx-auto max-w-3xl lg:grid-cols-2")}>
            {earlyBird.enabled && (
              <Reveal className="h-full">
                <div className="relative flex h-full flex-col rounded-3xl border border-brand/40 bg-card p-7 shadow-[0_20px_60px_-30px] shadow-brand/40">
                  <span className="absolute -top-3 left-7 rounded-full bg-brand px-3 py-1 font-mono text-[11px] uppercase tracking-[0.1em] text-brand-foreground">
                    {t("pricing.earlyBird.badge")}
                  </span>
                  <h3 className="font-display text-xl font-bold tracking-tight">{t("pricing.earlyBird.name")}</h3>
                  <p className="mt-4 flex items-baseline gap-1">
                    <span className="font-display text-5xl font-extrabold tracking-tight">$0</span>
                    <span className="text-sm text-muted-foreground">{t("pricing.period.free")}</span>
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{t("pricing.earlyBird.description")}</p>
                  <ul className="mt-6 flex-1 space-y-3 text-sm">
                    {[
                      `${formatHours(earlyBird.minuteLimit)} of video every month`,
                      `${earlyBird.resolution} clips`,
                      `YouTube videos up to ${earlyBird.youtubeMaxMinutes} minutes`,
                      t("pricing.tracking"),
                      t("pricing.exports"),
                    ].map((line) => (
                      <li key={line} className="flex gap-2.5">
                        <Check className="mt-0.5 size-4 shrink-0 text-brand" aria-hidden />
                        {line}
                      </li>
                    ))}
                  </ul>
                  <Button asChild className="mt-8 h-11 rounded-full">
                    <Link href="/sign-up">{t("pricing.earlyBird.cta")}</Link>
                  </Button>
                </div>
              </Reveal>
            )}
            {paidPlans.map((plan, index) => (
              <Reveal key={plan.id} delay={(index + 1) * 0.08} className="h-full">
                <div className="flex h-full flex-col rounded-3xl border bg-card p-7">
                  <h3 className="font-display text-xl font-bold tracking-tight">{plan.name}</h3>
                  <p className="mt-4 flex items-baseline gap-1">
                    <span className="font-display text-5xl font-extrabold tracking-tight">${planPrice(plan, "month")}</span>
                    <span className="text-sm text-muted-foreground">{t("pricing.period.month")}</span>
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{t(`pricing.${plan.id}.description`)}</p>
                  <ul className="mt-6 flex-1 space-y-3 text-sm">
                    {[...plan.highlights, t("pricing.tracking"), t("pricing.exports")].map((line) => (
                      <li key={line} className="flex gap-2.5">
                        <Check className="mt-0.5 size-4 shrink-0 text-brand" aria-hidden />
                        {line}
                      </li>
                    ))}
                  </ul>
                  <Button asChild variant="outline" className="mt-8 h-11 rounded-full">
                    <Link href="/sign-up">{t(`pricing.${plan.id}.cta`)}</Link>
                  </Button>
                </div>
              </Reveal>
            ))}
          </div>
          <p className="mt-8 text-center text-xs text-muted-foreground">{t("pricing.note")}</p>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="px-3 pb-24 pt-8 md:pb-32">
        <Reveal>
          <div className="mx-auto max-w-5xl rounded-[2rem] bg-[#0d0b0a] px-6 py-20 text-center text-[#f4f2ed] md:px-12">
            <h2 className="font-display text-4xl font-extrabold leading-[1.05] tracking-tight text-balance sm:text-5xl">
              {t("cta.title")}
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-[#f4f2ed]/70">{t("cta.body")}</p>
            <div className="mt-10 flex justify-center">
              <Button asChild size="lg" className="h-12 rounded-full px-7 text-sm">
                <Link href="/sign-up">
                  {t("cta.button")}
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
            </div>
          </div>
        </Reveal>
      </section>

      <SiteFooter />
    </div>
  );
}
