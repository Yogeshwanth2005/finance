"""add rag insurance documents and chat tables

Revision ID: a1f8c9e0d1b2
Revises: 6eed1f0685fe
Create Date: 2026-09-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1f8c9e0d1b2'
down_revision: Union[str, None] = '6eed1f0685fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'insurance_documents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('planId', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('sourceType', sa.String(), server_default='pdf', nullable=False),
        sa.Column('status', sa.String(), server_default='active', nullable=False),
        sa.Column('totalChunks', sa.Integer(), server_default='0', nullable=False),
        sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updatedAt', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['planId'], ['insurance_plan_reference.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_insurance_documents_planId', 'insurance_documents', ['planId'], unique=False)
    op.create_index('ix_insurance_documents_status', 'insurance_documents', ['status'], unique=False)

    op.create_table(
        'insurance_document_chunks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('documentId', sa.String(), nullable=False),
        sa.Column('chunkIndex', sa.Integer(), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('embedding', sa.JSON(), nullable=False),
        sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['documentId'], ['insurance_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_insurance_document_chunks_documentId', 'insurance_document_chunks', ['documentId'], unique=False)

    op.create_table(
        'insurance_chat_messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('userId', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('sources', sa.JSON(), nullable=False),
        sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['userId'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_insurance_chat_messages_userId_createdAt', 'insurance_chat_messages', ['userId', 'createdAt'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_insurance_chat_messages_userId_createdAt', table_name='insurance_chat_messages')
    op.drop_table('insurance_chat_messages')
    op.drop_index('ix_insurance_document_chunks_documentId', table_name='insurance_document_chunks')
    op.drop_table('insurance_document_chunks')
    op.drop_index('ix_insurance_documents_status', table_name='insurance_documents')
    op.drop_index('ix_insurance_documents_planId', table_name='insurance_documents')
    op.drop_table('insurance_documents')
