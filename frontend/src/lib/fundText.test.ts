import { describe, expect, it } from "vitest";

import { fundCount, fundRefetchDelay, maxNote } from "@/lib/fundText";

describe("fundRefetchDelay", () => {
  it("polls every 5 s while the server is warming, whatever else is pending", () => {
    expect(fundRefetchDelay("warming", false)).toBe(5_000);
    expect(fundRefetchDelay("warming", true)).toBe(5_000);
  });

  it("polls every 30 s while the data is unavailable", () => {
    expect(fundRefetchDelay("unavailable", false)).toBe(30_000);
    expect(fundRefetchDelay("unavailable", true)).toBe(30_000);
  });

  it("polls every 15 s while first NAVs are still being worked out, on fresh or stale data", () => {
    expect(fundRefetchDelay("ready", true)).toBe(15_000);
    expect(fundRefetchDelay("stale", true)).toBe(15_000);
  });

  it("never polls once the data is settled, or before the first answer", () => {
    expect(fundRefetchDelay("ready", false)).toBe(false);
    expect(fundRefetchDelay("stale", false)).toBe(false);
    expect(fundRefetchDelay(undefined, undefined)).toBe(false);
  });
});

describe("maxNote", () => {
  it("says the Max returns are still being calculated while first NAVs are missing", () => {
    expect(maxNote(true)).toMatch(/still being calculated/);
  });

  it("otherwise says Max is approximate and not like-for-like", () => {
    expect(maxNote(false)).toMatch(/month-start snapshot/);
    expect(maxNote(false)).toMatch(/not like-for-like/);
  });
});

describe("fundCount", () => {
  it("pluralises", () => {
    expect([0, 1, 2, 89].map(fundCount)).toEqual(["0 funds", "1 fund", "2 funds", "89 funds"]);
  });
});
