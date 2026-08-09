"""Zeitstempel je Aktion für DVW-Import (Roadmap 2.6)

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-09

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scout_actions",
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scout_actions", "created_at")
