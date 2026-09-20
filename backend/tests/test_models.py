from app.models import (
    User,
    FinancialProfile,
    ExistingDebt,
    InsuranceProfile,
    AllocationResult,
    GapAnalysisResult,
    FundReference,
    InsurancePlanReference,
    InsuranceDocument,
    InsuranceDocumentChunk,
    InsuranceChatMessage,
)


def test_table_names_match_prisma_map():
    assert User.__tablename__ == "users"
    assert FinancialProfile.__tablename__ == "financial_profile"
    assert ExistingDebt.__tablename__ == "existing_debt"
    assert InsuranceProfile.__tablename__ == "insurance_profile"
    assert AllocationResult.__tablename__ == "allocation_results"
    assert GapAnalysisResult.__tablename__ == "gap_analysis_results"
    assert FundReference.__tablename__ == "fund_reference"
    assert InsurancePlanReference.__tablename__ == "insurance_plan_reference"
    assert InsuranceDocument.__tablename__ == "insurance_documents"
    assert InsuranceDocumentChunk.__tablename__ == "insurance_document_chunks"
    assert InsuranceChatMessage.__tablename__ == "insurance_chat_messages"


def test_financial_profile_column_names_are_exact_camel_case():
    columns = {c.name for c in FinancialProfile.__table__.columns}
    assert "monthlyIncome" in columns
    assert "investmentHorizonYears" in columns
    assert "monthly_income" not in columns


def test_rag_models_column_names_are_exact_camel_case():
    doc_cols = {c.name for c in InsuranceDocument.__table__.columns}
    assert "planId" in doc_cols
    assert "totalChunks" in doc_cols
    assert "sourceType" in doc_cols

    chunk_cols = {c.name for c in InsuranceDocumentChunk.__table__.columns}
    assert "documentId" in chunk_cols
    assert "chunkIndex" in chunk_cols

    chat_cols = {c.name for c in InsuranceChatMessage.__table__.columns}
    assert "userId" in chat_cols

