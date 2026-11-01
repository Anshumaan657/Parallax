"""Add GitHub repository branch and webhook configuration.

Revision ID: 20261101_0010
Revises: 20261025_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261101_0010"
down_revision: str | None = "20261025_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "repositories",
        sa.Column("webhook_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "repositories",
        sa.Column(
            "webhook_events",
            sa.JSON(),
            nullable=False,
            server_default='["opened", "reopened", "synchronize", "ready_for_review"]',
        ),
    )


def downgrade() -> None:
    op.drop_column("repositories", "webhook_events")
    op.drop_column("repositories", "webhook_enabled")
