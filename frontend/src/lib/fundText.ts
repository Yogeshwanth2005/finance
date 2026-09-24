import type { FundsStatus } from "@/lib/types";

// How long to wait before asking the server again, or false to stop polling.
// warming: the server has no rows yet and is filling them; unavailable: AMFI could not be reached, so retry slowly;
// maxPending: a background pass is still working out first NAVs, which the Max window needs. Otherwise the data is settled.
export function fundRefetchDelay(status: FundsStatus | undefined, maxPending: boolean | undefined): number | false {
  if (status === "warming") return 5_000;
  if (status === "unavailable") return 30_000;
  if (maxPending) return 15_000;
  return false;
}

export function maxNote(maxPending: boolean): string {
  return maxPending
    ? "Max returns are still being calculated."
    : "Max is annualised from each fund's first NAV seen on a month-start snapshot, so it is approximate, and funds of different ages are not like-for-like.";
}

export function fundCount(count: number): string {
  return `${count} fund${count === 1 ? "" : "s"}`;
}
