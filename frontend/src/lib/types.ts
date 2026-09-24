export type RiskTolerance = "conservative" | "moderate" | "aggressive";

export interface ProfileInput {
  full_name: string;
  dob: string;
  age: number;
  city_tier: "tier_1" | "tier_2" | "tier_3";
  marital_status: "single" | "married";
  dependents: number;
  spouse_full_name: string;
  spouse_dob: string;
  spouse_age: number;
  spouse_employment_type: "mnc" | "business" | "freelance" | "not_working";
  employment_type: "mnc" | "business" | "freelance";
  annual_income: number;
  spouse_income: number;
  monthly_expenses: number;
  annual_bonus: number;
  home_loan: number;
  other_loans: number;
  monthly_emi: number;
  other_debts: number;
  current_health_cover_lakh: number;
  existing_term_cover_crore: number;
  emergency_savings: number;
  current_investments: number;
  risk_tolerance: RiskTolerance;
  investment_horizon_years: number;
}

export interface FamilyProfile extends ProfileInput {
  id: string;
}

export interface PlanDetails {
  eligibility: string;
  cover_range: string;
  waiting_periods: string;
  exclusions: string;
  riders: string;
  claim_terms: string;
}

// The editable card an admin reviews. Values the source document does not state are null / "Not stated in the document".
export interface PlanCardData {
  category: "term" | "health";
  name: string;
  provider: string;
  csr: string | null;
  annual_premium_from: number | null;
  cover_label: string | null;
  highlights: string[];
  fit: string | null;
  details: PlanDetails;
}

// A published card on the Insurance page: `id` and `source_title` identify the indexed document it came from.
export interface Plan extends PlanCardData {
  id: string;
  source_title: string;
}

export type PlanStatus = "none" | "draft" | "published";

export interface FinancialAnalysis {
  annual_household_income: number;
  annual_expenses: number;
  annual_emi: number;
  total_liabilities: number;
  annual_surplus_before_protection: number;
  annual_insurance_budget: number;
  investable_surplus: number;
  recommended_term_cover_crore: number;
  term_gap_crore: number;
  recommended_health_cover_lakh: number;
  health_gap_lakh: number;
  emergency_goal: number;
  emergency_gap: number;
  emergency_months: number;
  kpis: ProfileKpis;
  allocation: AllocationSnapshot;
  equity_split: EquitySplit;
  goal_check: GoalCheck;
  protection_score: number;
  score_label: string;
  formula_notes: string[];
  disclaimer: string;
}

// Glide-path split of the investable surplus, computed server-side from age, risk tolerance and horizon; sums to 100.
export interface AllocationSnapshot {
  equity_pct: number;
  debt_pct: number;
  gold_pct: number;
}

// Portfolio percentages of the large / mid / small cap slices; the three add up to allocation.equity_pct.
export interface EquitySplit {
  large_pct: number;
  mid_pct: number;
  small_pct: number;
}

// The mix's expected return against inflation plus a risk-scaled margin, and the March-2020-style crash line.
// `reachable` is null when it was not evaluated: the target is already met, or the horizon is short.
export interface GoalCheck {
  inflation_pct: number;
  margin_pct: number;
  target_pct: number;
  expected_return_pct: number;
  beats_target: boolean;
  reachable: boolean | null;
  suggestion_suppressed: boolean;
  min_equity_pct: number | null;
  crash_loss_pct: number;
  crash_loss_at_min_equity_pct: number | null;
}

export type FundSegment = "nifty" | "large" | "mid" | "small";
export type FundWindow = "1y" | "3y" | "5y" | "max";
// warming: the server has no rows yet and is filling them from AMFI; stale: older data after a failed refresh; unavailable: nothing loaded
export type FundsStatus = "warming" | "ready" | "stale" | "unavailable";

export interface FundRow {
  scheme_code: string;
  name: string;
  fund_house: string;
  category: string;
  segment: FundSegment | null;
  nav: number;
  nav_date: string;
  start_date: string | null;
  returns: Record<FundWindow, number | null>;
  max_is_annualised: boolean | null;
}

export type FundSegmentLists = Record<FundSegment, FundRow[]>;

// One block of a search result: a segment ("large") or an AMFI category ("cat-flexi-cap-fund").
export interface FundSection {
  key: string;
  title: string;
  funds: FundRow[];
}

export interface FundsTopResponse {
  status: FundsStatus;
  as_of: string | null;
  window: FundWindow;
  max_pending: boolean;
  segments: FundSegmentLists;
}

export interface FundsSearchResponse {
  status: FundsStatus;
  as_of: string | null;
  window: FundWindow;
  max_pending: boolean;
  query: string;
  fund_houses: string[];
  sections: FundSection[];
}

export interface ProfileKpis {
  emergency_coverage_pct: number;
  runway_months: number;
  term_cover_adequacy_pct: number;
  health_cover_adequacy_pct: number;
  savings_rate_pct: number;
  debt_to_income_pct: number;
  cover_to_liabilities_ratio: number;
  liabilities_to_income_multiple: number;
}

export interface ProfileResponse {
  profile: FamilyProfile;
  analysis: FinancialAnalysis;
}

export interface ChatResponse {
  answer: string;
  suggested_follow_up: string;
  is_mocked: boolean;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: "user" | "admin";
  profile_complete: boolean;
  preferred_language: "en" | "hi" | "te" | "ta";
  notifications_enabled: boolean;
  privacy_mode: boolean;
  created_at: string;
}

export interface UserSettings {
  name?: string;
  preferred_language?: User["preferred_language"];
  notifications_enabled?: boolean;
  privacy_mode?: boolean;
}

export interface ChangePasswordInput {
  current_password: string;
  new_password: string;
}

export interface DocumentRecord {
  id: string;
  title: string;
  source_type: string;
  source_url: string | null;
  chunk_count: number;
  status: string;
  enabled: boolean;
  created_at: string;
  created_by: string;
  plan: PlanCardData | null;
  plan_status: PlanStatus;
}

export interface AdminOverview {
  total_users: number;
  completed_profiles: number;
  indexed_documents: number;
  active_documents: number;
  vector_chunks: number;
  user_questions: number;
}

export interface AdminUserRecord {
  id: string;
  name: string;
  email: string;
  role: string;
  profile_complete: boolean;
  created_at: string;
}

export interface AdminQuestionRecord {
  id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  question: string;
  created_at: string;
}

export interface ChatMessageRecord {
  id: string;
  role: "advisor" | "you";
  text: string;
  sources: string[];
  created_at: string;
}