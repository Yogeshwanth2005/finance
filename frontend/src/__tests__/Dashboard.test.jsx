import { test, vi, beforeEach, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "../pages/Dashboard.jsx";
import { apiClient } from "../api/client.js";

vi.mock("../api/client.js", () => ({ apiClient: { get: vi.fn() } }));

const SAMPLE_RESPONSE = {
  demo_mode: false,
  kpis: {
    emergency_fund_coverage_pct: 75, emergency_fund_status: "building", emergency_fund_gap: 60000,
    term_cover_adequacy_pct: 33.33, term_cover_gap: 4000000,
    health_cover_adequacy_pct: 60, health_cover_gap: 200000,
    savings_rate_pct: 20, debt_to_income_pct: 17.77,
  },
  allocation: { equity_pct: 70, debt_pct: 20, gold_pct: 10 },
  fund_examples: {},
  insurance_examples: {},
};

beforeEach(() => {
  vi.clearAllMocks();
});

test("renders KPI values once the dashboard data loads", async () => {
  apiClient.get.mockResolvedValue(SAMPLE_RESPONSE);

  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );

  await waitFor(() => expect(screen.getByText("75%")).toBeInTheDocument());
  expect(screen.getByText("70%")).toBeInTheDocument();
});
