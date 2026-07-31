"""Live-Scouting-Engine mit den Volleyball-Regeln (Indoor, parametrisierbar).

Reine Python-Logik ohne DB-Abhängigkeit. Der Zustand entsteht durch Anwenden von
Events (Event-Sourcing); `apply_event` ist der einzige Mutationspfad, sodass ein
Replay der persistierten `live_events` immer denselben Zustand ergibt. Undo wird
außerhalb gelöst (letztes Event löschen + Replay).

Regelumfang (DV4-Vorbild, Abschnitt "Regulation" der Funktionsanalyse):
- Best-of-N, Satz bis `points_per_set` (Entscheidungssatz bis `tiebreak_points`),
  jeweils mindestens `min_lead` Punkte Vorsprung
- Side-Out: gewinnt das annehmende Team den Ballwechsel, erhält es Aufschlagrecht
  und rotiert im Uhrzeigersinn
- Wechsel-Limit pro Satz und Team, Auszeiten-Limit pro Satz und Team
- Aufstellungen: 6 eindeutige Spieler, Zonenreihenfolge [1, 6, 5, 4, 3, 2] intern
  als Liste ab Zone 1 gegen den Uhrzeigersinn gespeichert: Index 0 = Zone 1 usw.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

Side = Literal["home", "away"]

SIDES: tuple[Side, Side] = ("home", "away")


class RuleViolation(Exception):
    """Eingabe verletzt eine Volleyball-Regel oder den Spielablauf."""


@dataclass(frozen=True)
class Rules:
    best_of: int = 5
    points_per_set: int = 25
    tiebreak_points: int = 15
    min_lead: int = 2
    players_on_court: int = 6
    substitutions_per_set: int = 6
    timeouts_per_set: int = 2

    @property
    def sets_to_win(self) -> int:
        return self.best_of // 2 + 1


@dataclass
class SetState:
    number: int
    serving: Side
    lineups: dict[Side, list[int]]  # Index 0 = Zone 1, dann 2,3,4,5,6
    points: dict[Side, int] = field(default_factory=lambda: {"home": 0, "away": 0})
    substitutions: dict[Side, int] = field(default_factory=lambda: {"home": 0, "away": 0})
    timeouts: dict[Side, int] = field(default_factory=lambda: {"home": 0, "away": 0})
    rally_count: int = 0
    finished: bool = False


def _other(side: Side) -> Side:
    return "away" if side == "home" else "home"


class MatchEngine:
    def __init__(self, rules: Rules | None = None) -> None:
        self.rules = rules or Rules()
        self.sets_won: dict[Side, int] = {"home": 0, "away": 0}
        self.set_history: list[SetState] = []
        self.current_set: SetState | None = None

    # ------------------------------------------------------------------ replay

    def apply_event(self, event_type: str, payload: dict[str, Any]) -> None:
        handlers = {
            "start_set": self._on_start_set,
            "rally": self._on_rally,
            "substitution": self._on_substitution,
            "timeout": self._on_timeout,
            "correct_lineup": self._on_correct_lineup,
        }
        if event_type not in handlers:
            raise RuleViolation(f"Unbekannter Event-Typ: {event_type}")
        handlers[event_type](payload)

    @classmethod
    def replay(cls, rules: Rules, events: list[tuple[str, dict[str, Any]]]) -> "MatchEngine":
        engine = cls(rules)
        for event_type, payload in events:
            engine.apply_event(event_type, payload)
        return engine

    # ---------------------------------------------------------------- handlers

    def _on_start_set(self, payload: dict[str, Any]) -> None:
        if self.match_finished:
            raise RuleViolation("Das Match ist bereits beendet.")
        if self.current_set is not None and not self.current_set.finished:
            raise RuleViolation("Der laufende Satz ist noch nicht beendet.")

        serving = _validate_side(payload.get("serving"))
        lineups: dict[Side, list[int]] = {}
        for side in SIDES:
            lineup = payload.get(f"{side}_lineup")
            if not isinstance(lineup, list) or len(lineup) != self.rules.players_on_court:
                raise RuleViolation(
                    f"Aufstellung {side}: genau {self.rules.players_on_court} "
                    "Spielernummern erforderlich."
                )
            numbers = [int(n) for n in lineup]
            if len(set(numbers)) != len(numbers):
                raise RuleViolation(f"Aufstellung {side}: Spielernummern müssen eindeutig sein.")
            lineups[side] = numbers

        self.current_set = SetState(
            number=len(self.set_history) + 1, serving=serving, lineups=lineups
        )

    def _on_rally(self, payload: dict[str, Any]) -> None:
        current = self._require_running_set()
        winner = _validate_side(payload.get("winner"))

        if winner != current.serving:
            # Side-Out: Aufschlagrecht wechselt, das neue Aufschlagteam rotiert im
            # Uhrzeigersinn (Zone-2-Spieler geht in Zone 1 zum Aufschlag).
            lineup = current.lineups[winner]
            current.lineups[winner] = lineup[1:] + lineup[:1]
            current.serving = winner

        current.points[winner] += 1
        current.rally_count += 1

        if self._set_point_reached(current):
            current.finished = True
            self.sets_won[winner] += 1
            self.set_history.append(current)

    def _on_substitution(self, payload: dict[str, Any]) -> None:
        current = self._require_running_set()
        side = _validate_side(payload.get("side"))
        player_out = int(payload["player_out"])
        player_in = int(payload["player_in"])

        if current.substitutions[side] >= self.rules.substitutions_per_set:
            raise RuleViolation(
                f"Wechsellimit erreicht ({self.rules.substitutions_per_set} pro Satz)."
            )
        lineup = current.lineups[side]
        if player_out not in lineup:
            raise RuleViolation(f"Spieler {player_out} steht nicht auf dem Feld.")
        if player_in in lineup:
            raise RuleViolation(f"Spieler {player_in} steht bereits auf dem Feld.")

        lineup[lineup.index(player_out)] = player_in
        current.substitutions[side] += 1

    def _on_correct_lineup(self, payload: dict[str, Any]) -> None:
        # Reine Korrektur einer falsch erfassten Aufstellung/Rotation (z. B. verpasste
        # Seitenwechsel-Rotation) — zählt bewusst NICHT gegen das Wechsellimit und
        # ist kein regulärer Spielzug, siehe DV4-Vorbild „LINEUP" im Command Window
        # bzw. die "Ganzteam-Rotation"-Pfeile in vergleichbaren Tools.
        current = self._require_running_set()
        side = _validate_side(payload.get("side"))
        lineup = payload.get("lineup")
        if not isinstance(lineup, list) or len(lineup) != self.rules.players_on_court:
            raise RuleViolation(
                f"Aufstellung {side}: genau {self.rules.players_on_court} "
                "Spielernummern erforderlich."
            )
        numbers = [int(n) for n in lineup]
        if len(set(numbers)) != len(numbers):
            raise RuleViolation(f"Aufstellung {side}: Spielernummern müssen eindeutig sein.")
        current.lineups[side] = numbers

    def _on_timeout(self, payload: dict[str, Any]) -> None:
        current = self._require_running_set()
        side = _validate_side(payload.get("side"))
        if current.timeouts[side] >= self.rules.timeouts_per_set:
            raise RuleViolation(f"Auszeitlimit erreicht ({self.rules.timeouts_per_set} pro Satz).")
        current.timeouts[side] += 1

    # ------------------------------------------------------------------- rules

    def _set_point_reached(self, current: SetState) -> bool:
        target = (
            self.rules.tiebreak_points
            if current.number == self.rules.best_of
            else self.rules.points_per_set
        )
        home, away = current.points["home"], current.points["away"]
        return max(home, away) >= target and abs(home - away) >= self.rules.min_lead

    def _require_running_set(self) -> SetState:
        if self.match_finished:
            raise RuleViolation("Das Match ist bereits beendet.")
        if self.current_set is None or self.current_set.finished:
            raise RuleViolation("Kein laufender Satz — zuerst einen Satz starten.")
        return self.current_set

    # ------------------------------------------------------------------- state

    @property
    def match_finished(self) -> bool:
        return max(self.sets_won.values()) >= self.rules.sets_to_win

    def state(self) -> dict[str, Any]:
        current = self.current_set
        set_running = current is not None and not current.finished
        return {
            "sets_won": dict(self.sets_won),
            "match_finished": self.match_finished,
            "set_running": set_running,
            "set_scores": [
                {
                    "number": s.number,
                    "home": s.points["home"],
                    "away": s.points["away"],
                    "lineups": {side: list(s.lineups[side]) for side in SIDES},
                }
                for s in self.set_history
            ],
            "current_set": None
            if not set_running
            else {
                "number": current.number,
                "points": dict(current.points),
                "serving": current.serving,
                "lineups": {side: list(current.lineups[side]) for side in SIDES},
                "substitutions": dict(current.substitutions),
                "timeouts": dict(current.timeouts),
                "rally_count": current.rally_count,
            },
        }


def _validate_side(value: Any) -> Side:
    if value not in SIDES:
        raise RuleViolation(f"Ungültige Seite: {value!r} (erwartet 'home' oder 'away').")
    return value
