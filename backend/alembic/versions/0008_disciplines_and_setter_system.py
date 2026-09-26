"""Mehrfach-Formate (Halle 6:6/4:4/3:3/2:2, Beach 2:2) + Zuspielsystem

Bestehende Matches sind alle 6:6-Hallenspiele — server_default füllt sie
konsistent nach (discipline="hall_6", players_on_court=6, siehe
app/engine/disciplines.py).

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-26

"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("discipline", sa.String(16), nullable=False, server_default="hall_6"),
    )
    op.add_column(
        "matches",
        sa.Column("players_on_court", sa.Integer(), nullable=False, server_default="6"),
    )
    op.alter_column("matches", "discipline", server_default=None)
    op.alter_column("matches", "players_on_court", server_default=None)
    op.add_column("teams", sa.Column("setter_system", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("teams", "setter_system")
    op.drop_column("matches", "players_on_court")
    op.drop_column("matches", "discipline")
