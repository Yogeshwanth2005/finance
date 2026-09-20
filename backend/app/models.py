from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class User(BaseModel):
    id: str
    email: str
    created_at: Optional[datetime] = None

class FinancialProfile(BaseModel):
    userId: str
    annual_income: float
    monthly_expenses: float
    emergency_savings: float
    home_loan_outstanding: float = 0.0
    other_loans_outstanding: float = 0.0
    monthly_emi: float = 0.0
    annual_bonus: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class InsuranceProfile(BaseModel):
    userId: str
    personal_health_cover: float = 0.0
    employer_health_cover: float = 0.0
    existing_term_cover: float = 0.0
    dependents_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class GapAnalysisResult(BaseModel):
    userId: str
    emergency_fund_gap: float
    term_cover_gap: float
    health_cover_gap: float
    protection_score: int
    computed_at: datetime = Field(default_factory=datetime.utcnow)

class AllocationResult(BaseModel):
    userId: str
    equity_pct: float
    debt_pct: float
    gold_pct: float
    recommended_funds: List[dict]
    computed_at: datetime = Field(default_factory=datetime.utcnow)
