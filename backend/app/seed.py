from datetime import date

from app.db import SessionLocal
from app.models import FundReference, InsurancePlanReference

NAV_DATE = date(2026, 9, 1)

FUNDS = [
    {"schemeCode": "HDFC-TOP100-G", "schemeName": "HDFC Top 100 Fund", "amcName": "HDFC Mutual Fund", "category": "equity_large_cap", "expenseRatio": 1.05, "aumCr": 28500, "latestNav": 987.32, "externalUrl": "https://www.hdfcfund.com/"},
    {"schemeCode": "ICICI-BLUECHIP-G", "schemeName": "ICICI Prudential Bluechip Fund", "amcName": "ICICI Prudential Mutual Fund", "category": "equity_large_cap", "expenseRatio": 0.98, "aumCr": 45200, "latestNav": 112.45, "externalUrl": "https://www.icicipruamc.com/"},
    {"schemeCode": "SBI-BLUECHIP-G", "schemeName": "SBI Bluechip Fund", "amcName": "SBI Mutual Fund", "category": "equity_large_cap", "expenseRatio": 1.12, "aumCr": 39800, "latestNav": 78.19, "externalUrl": "https://www.sbimf.com/"},
    {"schemeCode": "PPFAS-FLEXICAP-G", "schemeName": "Parag Parikh Flexi Cap Fund", "amcName": "PPFAS Mutual Fund", "category": "equity_diversified", "expenseRatio": 0.76, "aumCr": 82300, "latestNav": 84.61, "externalUrl": "https://amc.ppfas.com/"},
    {"schemeCode": "AXIS-FLEXICAP-G", "schemeName": "Axis Flexi Cap Fund", "amcName": "Axis Mutual Fund", "category": "equity_diversified", "expenseRatio": 1.02, "aumCr": 12400, "latestNav": 21.34, "externalUrl": "https://www.axismf.com/"},
    {"schemeCode": "MIRAE-LARGEMID-G", "schemeName": "Mirae Asset Large & Midcap Fund", "amcName": "Mirae Asset Mutual Fund", "category": "equity_diversified", "expenseRatio": 0.89, "aumCr": 34600, "latestNav": 132.87, "externalUrl": "https://www.miraeassetmf.co.in/"},
    {"schemeCode": "HDFC-SHORTTERM-G", "schemeName": "HDFC Short Term Debt Fund", "amcName": "HDFC Mutual Fund", "category": "debt_short_duration", "expenseRatio": 0.45, "aumCr": 15200, "latestNav": 29.87, "externalUrl": "https://www.hdfcfund.com/"},
    {"schemeCode": "ICICI-SHORTTERM-G", "schemeName": "ICICI Prudential Short Term Fund", "amcName": "ICICI Prudential Mutual Fund", "category": "debt_short_duration", "expenseRatio": 0.52, "aumCr": 21300, "latestNav": 54.32, "externalUrl": "https://www.icicipruamc.com/"},
    {"schemeCode": "AXIS-SHORTTERM-G", "schemeName": "Axis Short Term Fund", "amcName": "Axis Mutual Fund", "category": "debt_short_duration", "expenseRatio": 0.48, "aumCr": 8900, "latestNav": 27.11, "externalUrl": "https://www.axismf.com/"},
    {"schemeCode": "SBI-FD-1Y", "schemeName": "SBI Bank Fixed Deposit (1 Year)", "amcName": "State Bank of India", "category": "fixed_deposit", "expenseRatio": 0, "aumCr": 0, "latestNav": 1, "externalUrl": "https://sbi.co.in/"},
    {"schemeCode": "HDFCBANK-FD-1Y", "schemeName": "HDFC Bank Fixed Deposit (1 Year)", "amcName": "HDFC Bank", "category": "fixed_deposit", "expenseRatio": 0, "aumCr": 0, "latestNav": 1, "externalUrl": "https://www.hdfcbank.com/"},
    {"schemeCode": "ICICIBANK-FD-1Y", "schemeName": "ICICI Bank Fixed Deposit (1 Year)", "amcName": "ICICI Bank", "category": "fixed_deposit", "expenseRatio": 0, "aumCr": 0, "latestNav": 1, "externalUrl": "https://www.icicibank.com/"},
    {"schemeCode": "SBI-GOLDETF-G", "schemeName": "SBI Gold ETF", "amcName": "SBI Mutual Fund", "category": "gold_etf", "expenseRatio": 0.65, "aumCr": 3400, "latestNav": 61.24, "externalUrl": "https://www.sbimf.com/"},
    {"schemeCode": "HDFC-GOLDETF-G", "schemeName": "HDFC Gold ETF", "amcName": "HDFC Mutual Fund", "category": "gold_etf", "expenseRatio": 0.6, "aumCr": 2800, "latestNav": 60.87, "externalUrl": "https://www.hdfcfund.com/"},
    {"schemeCode": "NIPPON-GOLDBEES-G", "schemeName": "Nippon India ETF Gold BeES", "amcName": "Nippon India Mutual Fund", "category": "gold_etf", "expenseRatio": 0.55, "aumCr": 8100, "latestNav": 61.02, "externalUrl": "https://mf.nipponindiaim.com/"},
    {"schemeCode": "SGB-2023-24-S1", "schemeName": "Sovereign Gold Bond 2023-24 Series I", "amcName": "Reserve Bank of India", "category": "sovereign_gold_bond", "expenseRatio": 0, "aumCr": 0, "latestNav": 6062, "externalUrl": "https://www.rbi.org.in/"},
    {"schemeCode": "SGB-2023-24-S2", "schemeName": "Sovereign Gold Bond 2023-24 Series II", "amcName": "Reserve Bank of India", "category": "sovereign_gold_bond", "expenseRatio": 0, "aumCr": 0, "latestNav": 5923, "externalUrl": "https://www.rbi.org.in/"},
    {"schemeCode": "SGB-2022-23-S3", "schemeName": "Sovereign Gold Bond 2022-23 Series III", "amcName": "Reserve Bank of India", "category": "sovereign_gold_bond", "expenseRatio": 0, "aumCr": 0, "latestNav": 5741, "externalUrl": "https://www.rbi.org.in/"},
]

INSURANCE_PLANS = [
    {"insurerName": "HDFC Life", "planName": "HDFC Life Click 2 Protect Super", "planType": "term", "sumAssuredMin": 2500000, "sumAssuredMax": 20000000, "indicativePremiumNote": "Illustrative: ~₹12,000/yr for a 30-year-old, ₹1cr cover, 30-yr term", "claimSettlementRatioPct": 98.66, "avgClaimSettlementDays": 5, "keyFeatures": ["Level cover term plan", "Terminal illness benefit", "Optional critical illness rider"], "externalUrl": "https://www.hdfclife.com/", "sourceNote": "Illustrative figures for demo purposes — not sourced from a live insurer rate card."},
    {"insurerName": "ICICI Prudential Life", "planName": "ICICI Pru iProtect Smart", "planType": "term", "sumAssuredMin": 5000000, "sumAssuredMax": 50000000, "indicativePremiumNote": "Illustrative: ~₹13,500/yr for a 30-year-old, ₹1cr cover, 30-yr term", "claimSettlementRatioPct": 99.18, "avgClaimSettlementDays": 4, "keyFeatures": ["Life cover + optional health cover rider", "Special exit value option", "Accidental death benefit"], "externalUrl": "https://www.iciciprulife.com/", "sourceNote": "Illustrative figures for demo purposes — not sourced from a live insurer rate card."},
    {"insurerName": "Star Health", "planName": "Star Health Comprehensive Insurance Policy", "planType": "health", "sumAssuredMin": 500000, "sumAssuredMax": 2500000, "indicativePremiumNote": "Illustrative: ~₹9,000/yr for ₹5L cover, individual, age 30", "claimSettlementRatioPct": 92.3, "avgClaimSettlementDays": 12, "keyFeatures": ["Cashless hospitalization", "No room-rent capping", "Annual health check-up"], "externalUrl": "https://www.starhealth.in/", "sourceNote": "Illustrative figures for demo purposes — not sourced from a live insurer rate card."},
    {"insurerName": "HDFC ERGO", "planName": "HDFC ERGO Optima Secure", "planType": "health", "sumAssuredMin": 500000, "sumAssuredMax": 10000000, "indicativePremiumNote": "Illustrative: ~₹11,000/yr for ₹5L cover, individual, age 30", "claimSettlementRatioPct": 94.1, "avgClaimSettlementDays": 9, "keyFeatures": ["Unlimited restoration of sum insured", "Air ambulance cover", "No-claim bonus up to 50%"], "externalUrl": "https://www.hdfcergo.com/health-insurance", "sourceNote": "Illustrative figures for demo purposes — not sourced from a live insurer rate card."},
]


def main():
    db = SessionLocal()
    try:
        db.query(FundReference).delete()
        db.query(InsurancePlanReference).delete()

        for fund in FUNDS:
            db.add(FundReference(navDate=NAV_DATE, **fund))
        for plan in INSURANCE_PLANS:
            db.add(InsurancePlanReference(**plan))

        db.commit()
        print(f"Seeded {len(FUNDS)} funds and {len(INSURANCE_PLANS)} insurance plans.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
