"""per-key latency variance for consistency

Revision ID: 0002_key_consistency
Revises: 0001_initial
Create Date: 2026-07-05

Adds latency_n + latency_sq_sum to key_stats so per-key consistency
(1 - stddev/mean of a key's latencies) can be computed. Backfills existing rows
assuming zero variance so the running mean stays continuous.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_key_consistency"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "key_stats",
        sa.Column("latency_n", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "key_stats",
        sa.Column(
            "latency_sq_sum",
            sa.Float(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    # Seed existing rows: treat past attempts as samples at the mean (variance 0).
    op.execute(
        """
        UPDATE key_stats
        SET latency_n = attempts,
            latency_sq_sum = attempts * (avg_latency_ms * avg_latency_ms)
        WHERE avg_latency_ms IS NOT NULL AND attempts > 0
        """
    )


def downgrade() -> None:
    op.drop_column("key_stats", "latency_sq_sum")
    op.drop_column("key_stats", "latency_n")
