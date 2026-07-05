"""per-user AI-coach prompt overrides

Revision ID: 0003_user_prompts
Revises: 0002_key_consistency
Create Date: 2026-07-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_user_prompts"
down_revision: Union[str, None] = "0002_key_consistency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_prompts",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_system", sa.Text(), nullable=True),
        sa.Column("analysis_user", sa.Text(), nullable=True),
        sa.Column("drill_system", sa.Text(), nullable=True),
        sa.Column("drill_user", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_prompts")
