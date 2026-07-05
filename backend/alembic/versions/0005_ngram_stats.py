"""per-(user, layout, ngram) bigram statistics

Revision ID: 0005_ngram_stats
Revises: 0004_user_ai_config
Create Date: 2026-07-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_ngram_stats"
down_revision: Union[str, None] = "0004_user_ai_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ngram_stats",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("layout_id", sa.String(length=64), nullable=False),
        sa.Column("ngram", sa.String(length=8), nullable=False),
        sa.Column("n", sa.Integer(), server_default=sa.text("2"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("errors", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("avg_latency_ms", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("latency_n", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("latency_sq_sum", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("hitch_n", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_session_seq", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "layout_id", "ngram"),
    )


def downgrade() -> None:
    op.drop_table("ngram_stats")
