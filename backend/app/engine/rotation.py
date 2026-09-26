"""Zuspieler-Rotationsposition (Z1–Z6) aus Kader + tatsächlicher Aufstellung.

Eigenes Modul statt Teil von `match_engine.py`, da die Engine bewusst
roster-unabhängig bleibt (reines Event-Sourcing über Spielernummern, siehe
docs/ARCHITEKTUR.md). Geteilt zwischen `app/dvw/exporter.py` (Live-Strang-DVW-
Export) und `app/analyse_sync.py` (Ableitung des Analyse-Strangs aus
`live_events`, Roadmap 2.7) — beide brauchen dieselbe Regel, portiert aus
`setterZone()` in `frontend/src/components/RotationCourt.vue`.
"""

from app.models import Player


def setter_zone(roster: list[Player], lineup: list[int]) -> int | None:
    """Zone des Referenz-Zuspielers, falls der auf dem Feld steht, sonst
    Fallback auf den tatsächlich aufgestellten Zuspieler (Position "Zuspieler").
    """
    primary = next((p for p in roster if p.is_primary_setter), None)
    setter_number = primary.number if primary and primary.number in lineup else None
    if setter_number is None:
        on_court = next(
            (p for p in roster if p.position == "Zuspieler" and p.number in lineup), None
        )
        setter_number = on_court.number if on_court else None
    if setter_number is None or setter_number not in lineup:
        return None
    return lineup.index(setter_number) + 1
