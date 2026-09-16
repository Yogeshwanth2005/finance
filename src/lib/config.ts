/**
 * Editable configuration values (Implementation Plan v2, Section 8).
 * Change these to tune gap-analysis, allocation, and reference-matching behavior.
 */
export const config = {
  /** Months of expenses the emergency fund should cover. */
  emergency_fund_multiplier: 6,

  /** Multiplier applied to annual income to derive the recommended term cover. */
  income_replacement_multiplier: 10,

  /** Baseline recommended health cover amount, in INR. */
  health_cover_baseline: 500000,

  /** Interest rate (%) above which a debt is treated as high-interest for prioritization. */
  high_interest_debt_threshold: 12,

  /**
   * Constant used in the age-based glide path: base_equity_pct = this minus
   * age (e.g. 100 - age). No v1 source for this value — see decisions/log.md.
   */
  base_equity_age_constant: 100,

  /** Multiplier applied to base equity allocation based on stated risk tolerance. */
  risk_tolerance_multipliers: {
    conservative: 0.8,
    moderate: 1.0,
    aggressive: 1.2,
  },

  /** Investment horizon (years) at or below which the short-horizon shift applies. */
  short_horizon_threshold: 3,

  /** Percentage points shifted from equity to debt when the short-horizon threshold applies. */
  short_horizon_shift: 20,

  /**
   * Flat gold allocation, as a percentage of the portfolio (diversification
   * sleeve, not derived from age/risk/horizon). Capped by whatever's left
   * after equity, so it never pushes debt negative. No v1 source for this
   * value — see decisions/log.md.
   */
  gold_allocation_pct: 10,

  /** Number of reference fund examples shown per allocation category. */
  fund_examples_per_category: 3,

  /** Number of reference insurance plan examples shown per coverage gap type. */
  insurance_examples_per_gap_type: 2,

  /**
   * When true, enables reference fund examples (5.2), fund reference cards (6.2),
   * and insurance plan reference cards (6.3). When false, the app falls back to
   * v1's category-only behavior for these sections.
   */
  DEMO_MODE: true,
} as const;

export type AppConfig = typeof config;
