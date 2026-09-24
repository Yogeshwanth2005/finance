import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiGet } from "@/lib/api";
import type { FundRow, FundSegment, FundsSearchResponse, FundsStatus, FundsTopResponse, FundWindow } from "@/lib/types";

const PERIODS: { value: FundWindow; label: string; hint: string }[] = [
  { value: "1y", label: "1Y", hint: "Annualised return over the last year" },
  { value: "3y", label: "3Y", hint: "Annualised return over the last 3 years" },
  { value: "5y", label: "5Y", hint: "Annualised return over the last 5 years" },
  { value: "max", label: "Max", hint: "Annualised since the Direct plan's first NAV (Direct plans only exist from January 2013)" },
];

const SEGMENTS: { key: FundSegment; title: string }[] = [
  { key: "nifty", title: "Nifty 50 index" },
  { key: "large", title: "Large cap" },
  { key: "mid", title: "Mid cap" },
  { key: "small", title: "Small cap" },
];

// warming: the server is still fetching NAV histories, so ask again soon; unavailable: the server retries on the next request
const refetchDelay = (status?: FundsStatus) => (status === "warming" ? 5_000 : status === "unavailable" ? 30_000 : false);

const formatReturn = (value: number | null) => (value === null ? "—" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`);
// Dates arrive as ISO days; read them as UTC so a viewer west of Greenwich does not see the previous month.
const formatMonth = (isoDate: string) => new Date(isoDate).toLocaleDateString("en-IN", { month: "short", year: "numeric", timeZone: "UTC" });
const formatDay = (isoDate: string) => new Date(isoDate).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const houseName = (fundHouse: string) => fundHouse.replace(/ mutual fund$/i, "");

function FundList({ segment, title, rows, period }: { segment: FundSegment; title: string; rows: FundRow[]; period: FundWindow }) {
  return (
    <Card className="border-[#e4e1d8] bg-white shadow-none" data-testid={`fund-list-${segment}`}>
      <CardHeader className="p-5 pb-2">
        <CardTitle className="text-base font-semibold text-[#17181c]">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-5 pt-2">
        {rows.length === 0 ? (
          <p className="text-xs leading-5 text-[#8a8f99]" data-testid={`fund-list-${segment}-empty`}>No funds with enough history for this window.</p>
        ) : (
          <ol className="space-y-3">
            {rows.map((fund, index) => {
              const value = fund.returns[period];
              return (
                <li key={fund.scheme_code} className="flex items-start gap-3" data-testid={`fund-row-${fund.scheme_code}`}>
                  <span className="w-5 pt-0.5 text-right font-mono text-[11px] text-[#8a8f99]">{index + 1}</span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-semibold text-[#17181c]" title={fund.name}>{fund.name}</p>
                    <p className="truncate text-[11px] text-[#8a8f99]">
                      {houseName(fund.fund_house)} · since {formatMonth(fund.start_date)}
                      {period === "max" && !fund.max_is_annualised ? " · new fund, not annualised" : ""}
                    </p>
                  </div>
                  <span className={`font-mono text-sm font-bold tabular-nums ${value !== null && value < 0 ? "text-[#b91c1c]" : "text-[#0d7a5f]"}`}>{formatReturn(value)}</span>
                </li>
              );
            })}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}

export default function FundExplorer({ investmentBlocked }: { investmentBlocked: boolean }) {
  const [period, setPeriod] = useState<FundWindow>("3y");
  const [draft, setDraft] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const searching = submitted !== null;
  const trimmed = draft.trim();

  const top = useQuery({
    queryKey: ["funds", "top", period],
    queryFn: () => apiGet<FundsTopResponse>(`/funds/top?window=${period}`),
    enabled: !searching,
    retry: false,
    placeholderData: keepPreviousData,
    refetchInterval: (query) => refetchDelay(query.state.data?.status),
  });
  const search = useQuery({
    queryKey: ["funds", "search", submitted, period],
    queryFn: () => apiGet<FundsSearchResponse>(`/funds/search?q=${encodeURIComponent(submitted ?? "")}&window=${period}`),
    enabled: searching,
    retry: false,
    placeholderData: keepPreviousData,
    refetchInterval: (query) => refetchDelay(query.state.data?.status),
  });

  const active = searching ? search : top;
  const data = active.data;
  const lists = searching ? search.data?.groups : top.data?.segments;
  const showLists = data !== undefined && (data.status === "ready" || data.status === "stale");
  const noHouseMatched = searching && search.data !== undefined && showLists && search.data.fund_houses.length === 0;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (trimmed.length >= 2) setSubmitted(trimmed);
  }

  function clearSearch() {
    setSubmitted(null);
    setDraft("");
  }

  let notice: string | null = null;
  if (active.isError) notice = "Couldn't load fund data. Try again in a moment.";
  else if (data === undefined) notice = "Loading fund data…";
  else if (data.status === "warming") notice = "Refreshing fund data… this can take a minute after the server wakes up.";
  else if (data.status === "unavailable") notice = "Fund data is unavailable right now. We'll keep retrying.";

  return (
    <section className="mt-10" data-testid="fund-explorer">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#0d7a5f]">Fund explorer</p>
          <h2 className="mt-2 font-heading text-2xl font-semibold text-[#17181c]" data-testid="fund-explorer-title">Real funds for each slice.</h2>
        </div>
        <div role="group" aria-label="Return period" className="inline-flex self-start rounded-lg border border-[#e4e1d8] bg-white p-0.5 sm:self-auto" data-testid="fund-window-toggle">
          {PERIODS.map((option) => (
            <button
              key={option.value}
              type="button"
              aria-pressed={period === option.value}
              title={option.hint}
              onClick={() => setPeriod(option.value)}
              className={`rounded-md px-3 py-1 text-xs font-semibold transition-colors ${period === option.value ? "bg-[#17181c] text-white" : "text-[#5c5f66] hover:bg-[#f1efe9]"}`}
              data-testid={`fund-window-${option.value}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {investmentBlocked && (
        <p className="mt-4 rounded-lg border border-[#eddcbb] bg-[#fff9ef] px-4 py-3 text-xs leading-5 text-[#8a6b3d]" data-testid="fund-explorer-blocker-note">
          Your plan puts protection first: close the emergency-fund or insurance gap above before investing. You can still browse.
        </p>
      )}

      <form onSubmit={onSubmit} role="search" className="mt-4 flex gap-2">
        <label htmlFor="fund-search-input" className="sr-only">Search fund house</label>
        <Input
          id="fund-search-input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          maxLength={60}
          placeholder="Search fund house, e.g. HDFC"
          className="h-9 max-w-sm bg-white text-sm"
          data-testid="fund-search-input"
        />
        <Button type="submit" disabled={trimmed.length < 2} className="h-9 bg-[#17181c] px-4 text-white hover:bg-[#2a2c33]" data-testid="fund-search-submit">
          <Search className="size-4" />Search
        </Button>
      </form>

      {period === "max" && (
        <p className="mt-3 text-[11px] leading-5 text-[#8a8f99]" data-testid="fund-max-note">
          Max is annualised from each fund's first Direct-plan NAV, so funds of different ages are not like-for-like.
        </p>
      )}

      {searching && search.data && (
        <div className="mt-5 flex flex-wrap items-center justify-between gap-2" data-testid="fund-search-heading">
          <p className="text-sm text-[#5c5f66]">
            Results for “{search.data.query}”{search.data.fund_houses.length > 0 && <span className="text-[#8a8f99]"> · {search.data.fund_houses.map(houseName).join(", ")}</span>}
          </p>
          <Button type="button" variant="outline" size="sm" onClick={clearSearch} data-testid="fund-search-clear">Back to top 10</Button>
        </div>
      )}

      {notice && <p className="mt-5 text-sm leading-6 text-[#5c5f66]" data-testid="fund-status-message">{notice}</p>}

      {noHouseMatched && search.data && (
        <p className="mt-5 text-sm leading-6 text-[#5c5f66]" data-testid="fund-search-empty">No fund house matches “{search.data.query}”.</p>
      )}

      {showLists && lists && !noHouseMatched && (
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {SEGMENTS.filter(({ key }) => !searching || key !== "nifty" || lists.nifty.length > 0).map(({ key, title }) => (
            <FundList key={key} segment={key} title={title} rows={lists[key]} period={period} />
          ))}
        </div>
      )}

      {data?.as_of && (
        <p className="mt-4 text-[11px] leading-5 text-[#8a8f99]" data-testid="fund-as-of">
          {data.status === "stale" ? "Showing older data; a refresh is retrying. " : ""}NAV data as of {formatDay(data.as_of)}
          {data.failed_count > 0 ? ` · ${data.failed_count} fund${data.failed_count === 1 ? "" : "s"} left out (data could not be loaded)` : ""}.
        </p>
      )}
      <p className="mt-1 text-[11px] leading-5 text-[#8a8f99]" data-testid="fund-explorer-disclaimer">
        Direct Growth plans · data from AMFI and mfapi.in · past performance is not indicative of future returns.
      </p>
    </section>
  );
}
