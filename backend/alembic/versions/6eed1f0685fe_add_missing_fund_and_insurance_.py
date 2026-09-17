"""add missing fund and insurance reference columns

Revision ID: 6eed1f0685fe
Revises: 8b9caba8c3dc
Create Date: 2026-09-17 21:02:15.606383

This migration is hand-trimmed from the raw autogenerate output. The raw
diff also proposed dropping Prisma's own `_prisma_migrations` bookkeeping
table and a long list of cosmetic type-affinity changes (TEXT -> VARCHAR,
TIMESTAMP -> TIMESTAMPTZ, JSONB -> JSON, index/constraint renames) that
are artifacts of SQLAlchemy's autogenerate comparing against Prisma's
column definitions, not real schema fixes — none of that is applied here.
This migration does exactly one thing: adds the three columns that
`prisma/schema.prisma` already declared (2026-09-17) but that were never
migrated to the live DB, per the pending-migration note in
`.agents/projects/active-backlog.md`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6eed1f0685fe'
down_revision: Union[str, None] = '8b9caba8c3dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'fund_reference',
        sa.Column('aumCr', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'),
    )
    op.add_column(
        'insurance_plan_reference',
        sa.Column('claimSettlementRatioPct', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'),
    )
    op.add_column(
        'insurance_plan_reference',
        sa.Column('avgClaimSettlementDays', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('insurance_plan_reference', 'avgClaimSettlementDays')
    op.drop_column('insurance_plan_reference', 'claimSettlementRatioPct')
    op.drop_column('fund_reference', 'aumCr')
