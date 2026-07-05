"""per-user UI/training settings (cross-browser sync)

Revision ID: 0006_user_settings
Revises: 0005_ngram_stats
Create Date: 2026-07-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_user_settings"
down_revision: Union[str, None] = "0005_ngram_stats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theme", sa.String(length=16), server_default="system", nullable=False),
        sa.Column("layout_id", sa.String(length=64), server_default="ferris_sweep_colemak_dh", nullable=False),
        sa.Column("goal", sa.String(length=16), server_default="time", nullable=False),
        sa.Column("duration_s", sa.Integer(), server_default=sa.text("60"), nullable=False),
        sa.Column("word_count", sa.Integer(), server_default=sa.text("25"), nullable=False),
        sa.Column("target_wpm", sa.Integer(), server_default=sa.text("40"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
