"""Initiales Schema: teams, players, matches, match_sets, rallies, scout_actions, live_events

Revision ID: 0001
Revises:
Create Date: 2026-07-27

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(8), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
    )
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("last_name", sa.String(80), nullable=False),
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("position", sa.String(20), nullable=False),
        sa.Column("is_libero", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("team_id", "number", name="uq_player_team_number"),
    )
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_date", sa.Date(), nullable=False),
        sa.Column("competition", sa.String(120), nullable=False),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("best_of", sa.Integer(), nullable=False),
        sa.Column("points_per_set", sa.Integer(), nullable=False),
        sa.Column("tiebreak_points", sa.Integer(), nullable=False),
        sa.Column("substitutions_per_set", sa.Integer(), nullable=False),
        sa.Column("timeouts_per_set", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "match_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "match_id",
            sa.Integer(),
            sa.ForeignKey("matches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("home_points", sa.Integer(), nullable=False),
        sa.Column("away_points", sa.Integer(), nullable=False),
        sa.Column("finished", sa.Boolean(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.UniqueConstraint("match_id", "number", name="uq_set_match_number"),
    )
    op.create_table(
        "rallies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "set_id",
            sa.Integer(),
            sa.ForeignKey("match_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("serving_side", sa.String(4), nullable=False),
        sa.Column("winner_side", sa.String(4), nullable=False),
        sa.Column("home_score_after", sa.Integer(), nullable=False),
        sa.Column("away_score_after", sa.Integer(), nullable=False),
    )
    op.create_table(
        "scout_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "rally_id",
            sa.Integer(),
            sa.ForeignKey("rallies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("raw_code", sa.String(40), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("player_number", sa.Integer(), nullable=True),
        sa.Column("skill", sa.String(1), nullable=True),
        sa.Column("hit_type", sa.String(1), nullable=True),
        sa.Column("evaluation", sa.String(1), nullable=True),
        sa.Column("start_zone", sa.Integer(), nullable=True),
        sa.Column("end_zone", sa.Integer(), nullable=True),
    )
    op.create_table(
        "live_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "match_id",
            sa.Integer(),
            sa.ForeignKey("matches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("match_id", "seq", name="uq_event_match_seq"),
    )


def downgrade() -> None:
    for table in (
        "live_events",
        "scout_actions",
        "rallies",
        "match_sets",
        "matches",
        "players",
        "teams",
    ):
        op.drop_table(table)
