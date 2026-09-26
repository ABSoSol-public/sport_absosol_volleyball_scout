from app.engine.player_profile import (
    ProfileActionRow,
    aggregate_career_stats,
    attack_zone_tendencies,
    serve_zone_tendencies,
)

# Zwei "Matches" (unterschieden über match_id) eines einzelnen Spielers, mit
# wiederkehrenden Angriffszonen (4->6 zweimal, davon 1 Fehler; 2->1 einmal)
# und Aufschlagzonen (1->5 zweimal, 1->1 einmal), um sowohl die
# Karriereaggregation als auch die Tendenzgruppierung/-sortierung zu prüfen.
ACTIONS = [
    ProfileActionRow(match_id=1, skill="S", evaluation="#", start_zone=1, end_zone=5),
    ProfileActionRow(match_id=1, skill="S", evaluation="=", start_zone=1, end_zone=5),
    ProfileActionRow(match_id=1, skill="A", evaluation="#", start_zone=4, end_zone=6),
    ProfileActionRow(match_id=1, skill="A", evaluation="=", start_zone=4, end_zone=6),
    ProfileActionRow(match_id=2, skill="S", evaluation="+", start_zone=1, end_zone=1),
    ProfileActionRow(match_id=2, skill="A", evaluation="/", start_zone=2, end_zone=1),
    ProfileActionRow(match_id=2, skill="R", evaluation="#"),
    ProfileActionRow(match_id=2, skill="B", evaluation="#"),
]


def test_aggregate_career_stats_counts_matches_and_skills() -> None:
    career = aggregate_career_stats(ACTIONS)
    assert career.matches == 2
    assert career.actions == len(ACTIONS)
    assert career.serve.total == 3 and career.serve.aces == 1 and career.serve.errors == 1
    assert career.attack.total == 3 and career.attack.kills == 1 and career.attack.blocked == 1
    assert career.reception.total == 1 and career.reception.perfect == 1
    assert career.block.total == 1 and career.block.points == 1


def test_attack_zone_tendencies_grouped_and_sorted_by_frequency() -> None:
    tendencies = attack_zone_tendencies(ACTIONS)
    assert [(t.start_zone, t.end_zone, t.attempts) for t in tendencies] == [
        (4, 6, 2),
        (2, 1, 1),
    ]
    top = tendencies[0]
    assert top.positive == 1 and top.errors == 1 and top.blocked == 0
    assert top.efficiency == 0.0  # (1 kill - 1 error - 0 blocked) / 2 attempts


def test_serve_zone_tendencies_track_aces_and_positive_pct() -> None:
    tendencies = serve_zone_tendencies(ACTIONS)
    assert (1, 5, 2) == (tendencies[0].start_zone, tendencies[0].end_zone, tendencies[0].attempts)
    assert tendencies[0].positive == 1 and tendencies[0].errors == 1
    assert tendencies[0].positive_pct == 50.0


def test_min_attempts_filters_rare_combinations() -> None:
    tendencies = attack_zone_tendencies(ACTIONS, min_attempts=2)
    assert [(t.start_zone, t.end_zone) for t in tendencies] == [(4, 6)]
