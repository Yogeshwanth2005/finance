# Model to Table Mapping for Supabase REST Client
# Maps SQLAlchemy Model Class Names to actual PostgreSQL table names in Supabase.

TABLE_MAP = {
    "User": "users",
    "FinancialProfile": "financial_profile",
    "ExistingDebt": "existing_debt",
    "InsuranceProfile": "insurance_profile",
    "AllocationResult": "allocation_results",
    "GapAnalysisResult": "gap_analysis_results",
    "FundReference": "fund_reference",
    "InsurancePlanReference": "insurance_plan_reference",
    "InsuranceDocument": "insurance_documents",
    "InsuranceDocumentChunk": "insurance_document_chunks",
    "InsuranceChatMessage": "insurance_chat_messages",
}

def get_table_name(model_name: str) -> str:
    \"\"\"Returns the actual Supabase table name for a given model name.\"\"\"
    return TABLE_MAP.get(model_name, model_name.lower())
