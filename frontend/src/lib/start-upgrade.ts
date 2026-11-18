"use client";

import type { BillingInterval, BillingPlanId } from "@/lib/billing-plans";
import { EXISTING_SUBSCRIPTION_NEEDS_PAYMENT } from "@/lib/subscription-status";

async function requestCheckout(plan: BillingPlanId, interval: BillingInterval) {
  const response = await fetch("/api/billing/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan, interval }),
  });
  const data: { url?: string; error?: string; code?: string } = await response.json().catch(() => ({}));
  return { response, data };
}

/**
 * Sends the user to Stripe for `plan`, billed every `interval`. New subscribers get Checkout; existing
 * subscribers get the portal's plan-change confirmation (see the checkout route).
 */
export async function startUpgrade(
  plan: BillingPlanId,
  source: string,
  interval: BillingInterval = "month",
): Promise<void> {
  const { response, data } = await requestCheckout(plan, interval);
  if (data.code === EXISTING_SUBSCRIPTION_NEEDS_PAYMENT) {
    const portal = await fetch("/api/billing/portal", { method: "POST" });
    const portalData: { url?: string; error?: string } = await portal.json().catch(() => ({}));
    if (!portal.ok || !portalData.url) {
      throw new Error(portalData.error || data.error || "We couldn't open checkout. Please try again.");
    }
    window.location.href = portalData.url;
    return;
  }
  if (!response.ok || !data.url) {
    throw new Error(data.error || "We couldn't open checkout. Please try again.");
  }
  window.location.href = data.url;
}
