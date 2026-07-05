"""progressive key unlocking: streaks, per-layout progress, settings

Revision ID: 0007_progressive_unlock
Revises: 0006_user_settings
Create Date: 2026-07-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_progressive_unlock"
down_revision: Union[str, None] = "0006_user_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "key_stats",
        sa.Column("qualifying_streak", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "user_settings",
        sa.Column("progressive_unlock", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "user_settings",
        sa.Column("unlock_threshold_pct", sa.Integer(), server_default=sa.text("90"), nullable=False),
    )
    op.add_column(
        "user_settings",
        sa.Column("unlock_window_sessions", sa.Integer(), server_default=sa.text("3"), nullable=False),
    )
    op.create_table(
        "user_layout_progress",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("layout_id", sa.String(length=64), nullable=False),
        sa.Column("unlocked_count", sa.Integer(), server_default=sa.text("6"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "layout_id"),
    )
    # Grandfather every EXISTING user on every layout to "all keys unlocked"
    # (9999 is clamped to the layout's key count at read time), so introducing
    # progressive unlocking never restricts a current account. Accounts created
    # after this migration get no row and lazy-init to the initial small set.
    op.execute(
        """
        INSERT INTO user_layout_progress (user_id, layout_id, unlocked_count)
        SELECT u.id, l.id, 9999 FROM users u CROSS JOIN layouts l
        ON CONFLICT (user_id, layout_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("user_layout_progress")
    op.drop_column("user_settings", "unlock_window_sessions")
    op.drop_column("user_settings", "unlock_threshold_pct")
    op.drop_column("user_settings", "progressive_unlock")
    op.drop_column("key_stats", "qualifying_streak")
