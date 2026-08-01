"""Referenz-Zuspieler-Kennzeichnung (Rotationscode Z1-Z6)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-01

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "players",
        sa.Column("is_primary_setter", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("players", "is_primary_setter", server_default=None)


def downgrade() -> None:
    op.drop_column("players", "is_primary_setter")
