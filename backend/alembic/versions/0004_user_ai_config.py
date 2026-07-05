"""per-user AI provider configuration

Revision ID: 0004_user_ai_config
Revises: 0003_user_prompts
Create Date: 2026-07-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_user_ai_config"
down_revision: Union[str, None] = "0003_user_prompts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_ai_config",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False, server_default="ollama"),
        sa.Column("ollama_model", sa.String(length=128), nullable=True),
        sa.Column("mistral_model", sa.String(length=128), nullable=True),
        sa.Column("mistral_api_key_enc", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_ai_config")
