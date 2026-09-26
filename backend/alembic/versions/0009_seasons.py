"""Saisons + Match.season_id (Grundlage für Spielerprofile über mehrere Saisons)

Saison-Zuschnitt: 1. Juli - 30. Juni (siehe app/seasons.py). Bestehende
Matches werden anhand ihres match_date rückwirkend einer Saison zugeordnet
(Backfill unten) — die Grenzformel ist hier bewusst dupliziert statt aus
app/seasons.py importiert (Migrationsskripte sollen stabil bleiben, auch wenn
sich der Anwendungscode später ändert).

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-26

"""
from datetime import date

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _season_label_and_bounds(match_date: date) -> tuple[str, date, date]:
    year = match_date.year if match_date.month >= 7 else match_date.year - 1
    return f"{year}/{year + 1}", date(year, 7, 1), date(year + 1, 6, 30)


def upgrade() -> None:
    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(20), nullable=False, unique=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
    )
    op.add_column("matches", sa.Column("season_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_matches_season_id", "matches", "seasons", ["season_id"], ["id"]
    )

    # Backfill: bestehende Matches rückwirkend einer Saison zuordnen, damit
    # Spielerprofile (docs/SPIELERPROFILE.md) auch historische Matches nach
    # Saison aufschlüsseln können, nicht nur ab jetzt neu angelegte.
    connection = op.get_bind()
    season_id_by_label: dict[str, int] = {}
    for match_id, match_date in connection.execute(
        sa.text("SELECT id, match_date FROM matches")
    ).fetchall():
        label, start, end = _season_label_and_bounds(match_date)
        season_id = season_id_by_label.get(label)
        if season_id is None:
            existing = connection.execute(
                sa.text("SELECT id FROM seasons WHERE label = :label"), {"label": label}
            ).fetchone()
            if existing:
                season_id = existing[0]
            else:
                connection.execute(
                    sa.text(
                        "INSERT INTO seasons (label, start_date, end_date) "
                        "VALUES (:label, :start, :end)"
                    ),
                    {"label": label, "start": start, "end": end},
                )
                season_id = connection.execute(
                    sa.text("SELECT id FROM seasons WHERE label = :label"), {"label": label}
                ).fetchone()[0]
            season_id_by_label[label] = season_id
        connection.execute(
            sa.text("UPDATE matches SET season_id = :sid WHERE id = :mid"),
            {"sid": season_id, "mid": match_id},
        )


def downgrade() -> None:
    op.drop_constraint("fk_matches_season_id", "matches", type_="foreignkey")
    op.drop_column("matches", "season_id")
    op.drop_table("seasons")
