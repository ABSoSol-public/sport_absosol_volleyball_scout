"""Team-/Spieler-Nachbearbeitung: Jugendspieler-Kennzeichnung

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "players",
        sa.Column("is_youth_player", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("players", "is_youth_player", server_default=None)


def downgrade() -> None:
    op.drop_column("players", "is_youth_player")
