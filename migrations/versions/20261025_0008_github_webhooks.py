"""Persist verified GitHub webhook deliveries.

Revision ID: 20261025_0008
Revises: 20260913_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261025_0008"
down_revision: str | None = "20260913_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "github_webhook_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "repository_id",
            sa.Uuid(),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("delivery_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("action", sa.String(120)),
        sa.Column("repository_full_name", sa.String(255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("delivery_id", name="uq_github_webhook_delivery_id"),
    )
    op.create_index(
        "ix_github_webhook_deliveries_workspace_id",
        "github_webhook_deliveries",
        ["workspace_id"],
    )
    op.create_index(
        "ix_github_webhook_deliveries_repository_id",
        "github_webhook_deliveries",
        ["repository_id"],
    )
    op.create_index(
        "ix_github_webhook_workspace_created",
        "github_webhook_deliveries",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_github_webhook_workspace_created", table_name="github_webhook_deliveries")
    op.drop_index("ix_github_webhook_deliveries_repository_id", table_name="github_webhook_deliveries")
    op.drop_index("ix_github_webhook_deliveries_workspace_id", table_name="github_webhook_deliveries")
    op.drop_table("github_webhook_deliveries")
