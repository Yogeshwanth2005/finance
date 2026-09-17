import { describe, expect, test } from "vitest";
import { formatInr } from "./format";

describe("formatInr", () => {
  test("formats a whole number as INR currency", () => {
    expect(formatInr(240000)).toBe("₹2,40,000");
  });

  test("formats zero", () => {
    expect(formatInr(0)).toBe("₹0");
  });
});
