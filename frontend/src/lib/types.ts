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
}

export interface FamilyProfile extends ProfileInput {
  id: string;
}

export interface Plan {
  id: string;
  category: "term" | "health";
  name: string;
  provider: string;
  csr: string;
  annual_premium_from: number;
  cover_label: string;
  highlights: string[];
  fit: string;
}

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
  protection_score: number;
  score_label: string;
  formula_notes: string[];
  disclaimer: string;
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
  plans: Plan[];
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