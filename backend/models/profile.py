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


class Plan(BaseModel):
    id: str
    category: str
    name: str
    provider: str
    csr: str
    annual_premium_from: float
    cover_label: str
    highlights: list[str]
    fit: str


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
    protection_score: int
    score_label: str
    formula_notes: list[str]
    disclaimer: str


class ProfileResponse(BaseModel):
    profile: FamilyProfile
    analysis: FinancialAnalysis
    plans: list[Plan]


class ChatQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class ChatResponse(BaseModel):
    answer: str
    suggested_follow_up: str
    is_mocked: bool = True