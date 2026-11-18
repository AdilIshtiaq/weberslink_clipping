import { describe, expect, it } from "vitest";

import { intlLocale, negotiateLocale } from "./config";

describe("locale helpers", () => {
  it("always resolves to English", () => {
    expect(negotiateLocale()).toBe("en");
    expect(intlLocale("en")).toBe("en");
  });
});
