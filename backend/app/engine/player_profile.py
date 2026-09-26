"""Karrierestatistik & Tendenzen eines Spielers über mehrere Matches/Saisons.

Reine Berechnungslogik (DB-frei, wie `statistics.py`) — operiert auf bereits
geladenen Aktionsdaten eines *einzelnen* physischen Spielers (identifiziert
über `team_id` + Trikotnummer, siehe `app/player_data.py` fürs Laden aus der
DB und `app/api/players.py` fürs HTTP-Interface). Nutzt dieselben Skill-Formeln
wie die Einzel-Match-Statistik
(`add_serve_action`/`add_reception_action`/`add_attack_action`/`add_block_action` aus
`statistics.py`), aber über den gesamten Aktionspool eines Spielers
akkumuliert statt pro Match neu gruppiert.

**Zonen-/Kombinationstendenzen** (Nutzerwunsch: „ein spielerbasierendes
Playbook, nach Vorbild NFL"): NFL-Playbooks fassen zusammen, welche Spielzüge
ein Team/Spieler wie oft und wie erfolgreich einsetzt. Das volleyballnahe
Äquivalent aus den bereits vorhandenen Scout-Daten sind Angriffs-
Zonenkombinationen (`start_zone`→`end_zone`, aus dem Advanced Code bzw. dem
Klickpfad/Zonen-Helfer) und Aufschlag-Zielzonen — beides bereits vollständig
in `scout_actions` vorhanden (DVW-Import) bzw. optional bei der Live-
Direkteingabe. `attack_zone_tendencies`/`serve_zone_tendencies` gruppieren
danach und liefern Häufigkeit + Erfolgsquote je Kombination, absteigend nach
Häufigkeit sortiert — die "am meisten genutzten Spielzüge" stehen oben,
genau wie in einer Tendenz-Tabelle eines NFL-Scouting-Reports.
"""

from dataclasses import dataclass

from app.engine.statistics import (
    PlayerAttackStats,
    PlayerBlockStats,
    PlayerReceptionStats,
    PlayerServeStats,
    add_attack_action,
    add_block_action,
    add_reception_action,
    add_serve_action,
)


@dataclass
class ProfileActionRow:
    """Eine Aktion eines Spielers, angereichert um Match-Kontext (Match-ID
    fürs Zählen bestrittener Matches, Saison-ID für die Saison-Aufschlüsselung
    in `app/api/players.py`, Zonenfelder für die Tendenzanalyse)."""

    match_id: int
    skill: str | None
    evaluation: str | None
    season_id: int | None = None
    start_zone: int | None = None
    end_zone: int | None = None


@dataclass
class CareerSkillStats:
    serve: PlayerServeStats
    reception: PlayerReceptionStats
    attack: PlayerAttackStats
    block: PlayerBlockStats
    matches: int = 0
    actions: int = 0


def aggregate_career_stats(actions: list[ProfileActionRow]) -> CareerSkillStats:
    serve = PlayerServeStats(player_number=0)
    reception = PlayerReceptionStats(player_number=0)
    attack = PlayerAttackStats(player_number=0)
    block = PlayerBlockStats(player_number=0)
    match_ids: set[int] = set()
    for action in actions:
        match_ids.add(action.match_id)
        if action.skill == "S":
            add_serve_action(serve, action.evaluation)
        elif action.skill == "R":
            add_reception_action(reception, action.evaluation)
        elif action.skill == "A":
            add_attack_action(attack, action.evaluation)
        elif action.skill == "B":
            add_block_action(block, action.evaluation)
    return CareerSkillStats(
        serve=serve,
        reception=reception,
        attack=attack,
        block=block,
        matches=len(match_ids),
        actions=len(actions),
    )


@dataclass
class ZoneTendency:
    start_zone: int | None
    end_zone: int | None
    attempts: int = 0
    positive: int = 0  # Ass (Aufschlag) bzw. Kill (Angriff)
    errors: int = 0
    blocked: int = 0  # nur Angriff (gegnerischer Blockpunkt)

    @property
    def positive_pct(self) -> float | None:
        return (self.positive / self.attempts * 100) if self.attempts else None

    @property
    def efficiency(self) -> float | None:
        # Wie PlayerAttackStats.efficiency — für Aufschlag ist `blocked`
        # immer 0, reduziert sich also auf (Ass − Fehler) / Versuche.
        return ((self.positive - self.errors - self.blocked) / self.attempts) if self.attempts else None


def _zone_tendencies(
    actions: list[ProfileActionRow], skill: str, min_attempts: int
) -> list[ZoneTendency]:
    grouped: dict[tuple[int | None, int | None], ZoneTendency] = {}
    for action in actions:
        if action.skill != skill:
            continue
        key = (action.start_zone, action.end_zone)
        tendency = grouped.setdefault(key, ZoneTendency(start_zone=key[0], end_zone=key[1]))
        tendency.attempts += 1
        if action.evaluation == "#":
            tendency.positive += 1
        elif action.evaluation == "=":
            tendency.errors += 1
        elif skill == "A" and action.evaluation == "/":
            tendency.blocked += 1
    return sorted(
        (t for t in grouped.values() if t.attempts >= min_attempts),
        key=lambda t: (-t.attempts, t.start_zone or 0, t.end_zone or 0),
    )


def attack_zone_tendencies(actions: list[ProfileActionRow], min_attempts: int = 1) -> list[ZoneTendency]:
    return _zone_tendencies(actions, "A", min_attempts)


def serve_zone_tendencies(actions: list[ProfileActionRow], min_attempts: int = 1) -> list[ZoneTendency]:
    return _zone_tendencies(actions, "S", min_attempts)
