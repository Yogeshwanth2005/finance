from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ProfileInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    dob: str
    age: int = Field(ge=18, le=75)
    city_tier: str = Field(pattern="^(tier_1|tier_2|tier_3)$")
    marital_status: str = Field(pattern="^(single|married)$")
    dependents: int = Field(ge=0, le=12)
    spouse_full_name: str = ""
    spouse_dob: str = ""
    spouse_age: int = Field(default=0, ge=0, le=75)
    spouse_employment_type: str = Field(default="not_working", pattern="^(mnc|business|freelance|not_working)$")
    employment_type: str = Field(pattern="^(mnc|business|freelance)$")
    annual_income: float = Field(gt=0)
    spouse_income: float = Field(ge=0)
    monthly_expenses: float = Field(gt=0)
    annual_bonus: float = Field(ge=0)
    home_loan: float = Field(ge=0)
    other_loans: float = Field(ge=0)
    monthly_emi: float = Field(ge=0)
    other_debts: float = Field(ge=0)
    current_health_cover_lakh: float = Field(ge=0)
    existing_term_cover_crore: float = Field(ge=0)
    emergency_savings: float = Field(ge=0)
    current_investments: float = Field(ge=0)
    # Defaults keep profiles saved before these fields existed valid: _response() re-validates stored documents on every read.
    risk_tolerance: str = Field(default="moderate", pattern="^(conservative|moderate|aggressive)$")
    investment_horizon_years: int = Field(default=10, ge=1, le=60)

    @model_validator(mode="after")
    def clear_spouse_when_single(self) -> "ProfileInput":
        if self.marital_status == "single":
            self.spouse_full_name = ""
            self.spouse_dob = ""
            self.spouse_age = 0
            self.spouse_employment_type = "not_working"
            self.spouse_income = 0
        return self


class FamilyProfile(ProfileInput):
    id: str


class ProfileKpis(BaseModel):
    emergency_coverage_pct: float
    runway_months: float
    term_cover_adequacy_pct: float
    health_cover_adequacy_pct: float
    savings_rate_pct: float
    debt_to_income_pct: float
    cover_to_liabilities_ratio: float
    liabilities_to_income_multiple: float


class AllocationSnapshot(BaseModel):
    equity_pct: float
    debt_pct: float
    gold_pct: float


class EquitySplit(BaseModel):
    # Portfolio percentages: the three add up to allocation.equity_pct
    large_pct: float
    mid_pct: float
    small_pct: float


class GoalCheck(BaseModel):
    inflation_pct: float
    margin_pct: float
    target_pct: float
    expected_return_pct: float
    beats_target: bool
    reachable: bool | None  # None when not evaluated: the target is already met, or the horizon is short
    suggestion_suppressed: bool
    min_equity_pct: float | None
    crash_loss_pct: float
    crash_loss_at_min_equity_pct: float | None


class FinancialAnalysis(BaseModel):
    annual_household_income: float
    annual_expenses: float
    annual_emi: float
    total_liabilities: float
    annual_surplus_before_protection: float
    annual_insurance_budget: float
    investable_surplus: float
    recommended_term_cover_crore: float
    term_gap_crore: float
    recommended_health_cover_lakh: float
    health_gap_lakh: float
    emergency_goal: float
    emergency_gap: float
    emergency_months: float
    kpis: ProfileKpis
    allocation: AllocationSnapshot
    equity_split: EquitySplit
    goal_check: GoalCheck
    protection_score: int
    score_label: str
    formula_notes: list[str]
    disclaimer: str


class ProfileResponse(BaseModel):
    profile: FamilyProfile
    analysis: FinancialAnalysis


class ChatQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class ChatResponse(BaseModel):
    answer: str
    suggested_follow_up: str
    is_mocked: bool = True