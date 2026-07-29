"""Statistik-Auswertung: Setter-Positionen je Ballwechsel für die Rotationsanalyse

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rallies", sa.Column("home_setter_position", sa.Integer(), nullable=True))
    op.add_column("rallies", sa.Column("away_setter_position", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("rallies", "away_setter_position")
    op.drop_column("rallies", "home_setter_position")
