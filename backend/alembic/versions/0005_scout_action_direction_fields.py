"""Richtungserfassung: Angriffskombination/Setter-Call, Ziel-Angriff, Subzone

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scout_actions", sa.Column("attack_combination", sa.String(4), nullable=True))
    op.add_column("scout_actions", sa.Column("target_attack", sa.String(1), nullable=True))
    op.add_column("scout_actions", sa.Column("subzone", sa.String(1), nullable=True))


def downgrade() -> None:
    op.drop_column("scout_actions", "subzone")
    op.drop_column("scout_actions", "target_attack")
    op.drop_column("scout_actions", "attack_combination")
