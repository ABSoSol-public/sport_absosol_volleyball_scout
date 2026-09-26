"""Saison-Zuordnung für Matches (Grundlage für Spielerprofile über mehrere
Saisons hinweg, siehe docs/SPIELERPROFILE.md).

Eine Saison läuft **1. Juli – 30. Juni** — ein pragmatischer, für Hallen- wie
Beach-Saisons gleichermaßen brauchbarer Schnitt (die meisten deutschen
Hallensaisons laufen Herbst–Frühjahr über den Jahreswechsel, Beach-Saisons
Frühjahr–Herbst; ein Schnitt am 1. Juli trennt beide sauber in
aufeinanderfolgende Saisonlabel statt sie zu vermischen). Konfigurierbar nur
an dieser einen Stelle, falls sich das als falsch herausstellt.

**Bewusst dieselbe Grenzformel wie in der Migration** (`alembic/versions/
0009_seasons.py`, dort für den Altdaten-Backfill dupliziert statt importiert)
— Migrationsskripte sollen laut Alembic-Best-Practice stabil bleiben, auch
wenn sich Anwendungscode später ändert; eine Änderung hier wirkt sich deshalb
nicht rückwirkend auf bereits gelaufene Migrationen aus.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Season


def season_bounds_for_date(d: date) -> tuple[str, date, date]:
    year = d.year if d.month >= 7 else d.year - 1
    return f"{year}/{year + 1}", date(year, 7, 1), date(year + 1, 6, 30)


def get_or_create_season(db: Session, match_date: date) -> Season:
    label, start, end = season_bounds_for_date(match_date)
    season = db.scalar(select(Season).where(Season.label == label))
    if season is None:
        season = Season(label=label, start_date=start, end_date=end)
        db.add(season)
        db.flush()
    return season
