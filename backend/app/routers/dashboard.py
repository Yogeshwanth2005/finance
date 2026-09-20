from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.config import DEMO_MODE
from app.db import get_supabase
from app.demo_user import get_or_create_demo_user
from app.models import User
from app.mapping import get_table_name
from app.services.allocation import select_fund_examples
from app.services.insurance_matching import select_insurance_examples

router = APIRouter()

BUCKETS = ["equity", "debt", "gold"]


@router.get("/api/dashboard")
def get_dashboard(
    user: User = Depends(get_or_create_demo_user),
    supabase: Client = Depends(get_supabase),
):
    # Fetch Gap Analysis Result
    gap_res = supabase.table("gap_analysis_results").select("*").eq("userId", user.id).order("computedAt", desc=True).limit(1).execute()
    gap_result = gap_res.data[0] if gap_res.data else None

    # Fetch Allocation Result
    alloc_res = supabase.table("allocation_results").select("*").eq("userId", user.id).order("computedAt", desc=True).limit(1).execute()
    allocation_result = alloc_res.data[0] if alloc_res.data else None

    if gap_result is None or allocation_result is None:
        raise HTTPException(status_code=404, detail="No onboarding data yet")

    term_cover_gap = float(gap_result["termCoverGap"])
    health_cover_gap = float(gap_result["healthCoverGap"])

    fund_examples: dict[str, list[dict]] = {}
    insurance_examples: dict[str, list[dict]] = {}

    if DEMO_MODE:
        # Fetch all fund references
        funds_res = supabase.table("fund_reference").select("*").execute()
        funds = [
            {
                "id": f["id"], "scheme_name": f["schemeName"], "amc_name": f["amcName"],
                "category": f["category"], "expense_ratio": float(f["expenseRatio"]),
                "latest_nav": float(f["latestNav"]), "external_url": f["externalUrl"],
                "aum_cr": float(f["aumCr"]),
            }
            for f in funds_res.data
        ]
        for bucket in BUCKETS:
            examples = select_fund_examples(bucket, funds)
            if examples:
                fund_examples[bucket] = examples

        # Fetch all insurance plan references
        plans_res = supabase.table("insurance_plan_reference").select("*").execute()
        plans = [
            {
                "id": p["id"], "insurer_name": p["insurerName"], "plan_name": p["planName"],
                "plan_type": p["planType"], "sum_assured_min": float(p["sumAssuredMin"]),
                "sum_assured_max": float(p["sumAssuredMax"]), "key_features": p["keyFeatures"],
                "indicative_premium_note": p["indicativePremiumNote"],
                "claim_settlement_ratio_pct": float(p["claimSettlementRatioPct"]),
                "avg_claim_settlement_days": p["avgClaimSettlementDays"],
                "external_url": p["externalUrl"],
            }
            for p in plans_res.data
        ]
        for plan_type, gap in (("term", term_cover_gap), ("health", health_cover_gap)):
            if gap > 0:
                examples = select_insurance_examples(plan_type, gap, plans)
                if examples:
                    insurance_examples[plan_type] = examples

    return {
        "demo_mode": DEMO_MODE,
        "kpis": {
            "emergency_fund_coverage_pct": float(gap_result["emergencyFundCoveragePct"]),
            "emergency_fund_status": gap_result["emergencyFundStatus"],
            "emergency_fund_gap": max(0, float(gap_result["emergencyFundTarget"]) - float(gap_result["emergencyFundCurrent"])),
            "term_cover_adequacy_pct": float(gap_result["termCoverAdequacyPct"]),
            "term_cover_gap": term_cover_gap,
            "health_cover_adequacy_pct": float(gap_result["healthCoverAdequacyPct"]),
            "health_cover_gap": health_cover_gap,
            "savings_rate_pct": float(gap_result["savingsRatePct"]),
            "debt_to_income_pct": float(gap_result["debtToIncomePct"]),
        },
        "allocation": {
            "equity_pct": float(allocation_result["equityPct"]),
            "debt_pct": float(allocation_result["debtPct"]),
            "gold_pct": float(allocation_result["goldPct"]),
        },
        "fund_examples": fund_examples,
        "insurance_examples": insurance_examples,
    }
