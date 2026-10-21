import { describe, expect, it } from "vitest";

import { en, hi, translate } from "@/lib/i18n/dictionaries";

describe("dictionaries", () => {
  it("Hindi covers every English key with a non-empty string", () => {
    for (const key of Object.keys(en) as (keyof typeof en)[]) {
      expect(hi[key], key).toBeTruthy();
    }
    expect(Object.keys(hi).sort()).toEqual(Object.keys(en).sort());
  });

  it("interpolates variables and leaves unknown placeholders intact", () => {
    expect(translate(en, "common.page", { n: 3 })).toBe("Page 3");
    expect(translate(hi, "budget.of", { spent: "$0.10" })).toBe("{cap} में से $0.10");
  });
});
