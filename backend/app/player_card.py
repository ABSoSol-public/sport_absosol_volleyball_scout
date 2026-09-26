"""FIFA-Style Skill-Karte: Bewertung eines Spielers je Skill (0-100) relativ
zu allen anderen Spielern in der Datenbank mit ausreichend Aktionen in
derselben Disziplin (+ optional derselben Saison) — dynamisch aus den
tatsächlich gescouteten Daten berechnet statt aus festen Notenschwellen
(Nutzerwunsch: „Bewertung über die komplette Datenbank als Referenz über alle
Spieler hinweg ... muss dynamisch berechnet werden").

**Vergleichsgruppe ist bewusst auf dieselbe Disziplin beschränkt** — ein
Beach-Aufschlag ist nicht mit einem Hallen-Aufschlag vergleichbar (andere
Punktziele, andere Feldgröße), siehe docs/SPIELFORMATE.md. Die Karte nimmt
daher immer einen `discipline`-Filter entgegen, nie "alle Formate gemischt".

**Bewertungsformel**: Perzentilrang der Rohkennzahl (`_serve_metric` etc.,
siehe unten) innerhalb der Population aller Spieler mit mindestens
`MIN_SAMPLE[skill]` Aktionen in diesem Skill (die Zielspielerin/der
Zielspieler selbst zählt zur Population dazu — "wo stehst du im Vergleich zu
allen, dich eingeschlossen" ist die einfachste, unzweideutige Definition).
Ein Perzentilrang (statt z. B. z-Score) braucht keine
Normalverteilungsannahme und bleibt robust gegenüber Ausreißern — beides bei
den hier realistischen kleinen Vereins-Datenmengen wichtiger als bei einer
Profiliga mit tausenden Spielern. `overall` ist der Mittelwert der
Kategorien mit ausreichender Stichprobe; eine Kategorie ohne genug Daten
fließt **nicht** als 0 ein (das würde einen Spieler ohne Blockdaten fälschlich
so behandeln, als sei er im Block schlecht, statt schlicht ungetestet).

Die `MIN_SAMPLE`-Schwellen sind ein bewusst konservativer Startwert (genug,
um die extremsten Zufallsausreißer bei sehr wenigen Versuchen zu dämpfen),
keine statistisch hergeleitete Konstante — bei Bedarf anpassbar.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.player_profile import (
    CareerSkillStats,
    ProfileActionRow,
    aggregate_career_stats,
)
from app.engine.statistics import (
    PlayerAttackStats,
    PlayerBlockStats,
    PlayerReceptionStats,
    PlayerServeStats,
)
from app.models import Match, MatchSet, Rally, ScoutAction

MIN_SAMPLE = {"serve": 6, "reception": 6, "attack": 6, "block": 3}


def _serve_metric(s: PlayerServeStats) -> float | None:
    return (s.aces - s.errors) / s.total if s.total else None


def _reception_metric(r: PlayerReceptionStats) -> float | None:
    return r.positive_pct


def _attack_metric(a: PlayerAttackStats) -> float | None:
    return a.efficiency


def _block_metric(b: PlayerBlockStats) -> float | None:
    return (b.points / b.total) if b.total else None


# (Metrikformel, Stichprobengröße) je Kategorie — beide brauchen dieselbe
# `CareerSkillStats`-Instanz, daher als Funktionspaar statt zweier Dicts.
_CATEGORY_FUNCS = {
    "serve": (lambda c: _serve_metric(c.serve), lambda c: c.serve.total),
    "reception": (lambda c: _reception_metric(c.reception), lambda c: c.reception.total),
    "attack": (lambda c: _attack_metric(c.attack), lambda c: c.attack.total),
    "block": (lambda c: _block_metric(c.block), lambda c: c.block.total),
}


def _percentile_rank(value: float, population: list[float]) -> float:
    less = sum(1 for v in population if v < value)
    equal = sum(1 for v in population if v == value)
    return round(100 * (less + 0.5 * equal) / len(population), 1)


@dataclass
class SkillCategory:
    metric: float | None
    rating: float | None  # 0-100 Perzentilrang, None bei zu wenig Daten
    sample_size: int
    population_size: int


@dataclass
class SkillCard:
    team_id: int
    number: int
    discipline: str
    season_id: int | None
    categories: dict[str, SkillCategory]
    overall: float | None


def _load_all_player_actions(
    db: Session, discipline: str, season_id: int | None
) -> dict[tuple[int, int], list[ProfileActionRow]]:
    """Alle Aktionen aller Spieler dieser Disziplin(+Saison), gruppiert nach
    physischer Spieleridentität `(team_id, Spielernummer)` — die
    Vergleichspopulation für die Perzentilränge oben."""
    stmt = (
        select(
            Match.id,
            Match.home_team_id,
            Match.away_team_id,
            ScoutAction.side,
            ScoutAction.player_number,
            ScoutAction.skill,
            ScoutAction.evaluation,
        )
        .select_from(ScoutAction)
        .join(Rally, ScoutAction.rally_id == Rally.id)
        .join(MatchSet, Rally.set_id == MatchSet.id)
        .join(Match, MatchSet.match_id == Match.id)
        .where(Match.discipline == discipline)
        .where(ScoutAction.player_number.is_not(None))
    )
    if season_id is not None:
        stmt = stmt.where(Match.season_id == season_id)

    buckets: dict[tuple[int, int], list[ProfileActionRow]] = {}
    for match_id, home_id, away_id, side, number, skill, evaluation in db.execute(stmt).all():
        team_id = home_id if side == "home" else away_id
        buckets.setdefault((team_id, number), []).append(
            ProfileActionRow(match_id=match_id, skill=skill, evaluation=evaluation)
        )
    return buckets


def compute_skill_card(
    db: Session, team_id: int, number: int, discipline: str, season_id: int | None
) -> SkillCard:
    buckets = _load_all_player_actions(db, discipline, season_id)
    target_stats = aggregate_career_stats(buckets.get((team_id, number), []))
    population_stats: list[CareerSkillStats] = [
        aggregate_career_stats(actions) for actions in buckets.values()
    ]

    categories: dict[str, SkillCategory] = {}
    ratings: list[float] = []
    for name, (metric_fn, sample_fn) in _CATEGORY_FUNCS.items():
        min_sample = MIN_SAMPLE[name]
        target_sample = sample_fn(target_stats)
        target_metric = metric_fn(target_stats) if target_sample >= min_sample else None

        population_metrics = [
            metric
            for stats in population_stats
            if sample_fn(stats) >= min_sample and (metric := metric_fn(stats)) is not None
        ]

        rating = None
        if target_metric is not None and population_metrics:
            rating = _percentile_rank(target_metric, population_metrics)
            ratings.append(rating)

        categories[name] = SkillCategory(
            metric=target_metric,
            rating=rating,
            sample_size=target_sample,
            population_size=len(population_metrics),
        )

    overall = round(sum(ratings) / len(ratings), 1) if ratings else None
    return SkillCard(
        team_id=team_id,
        number=number,
        discipline=discipline,
        season_id=season_id,
        categories=categories,
        overall=overall,
    )
