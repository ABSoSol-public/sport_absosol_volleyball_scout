"""Parser für den Data-Volley-Main-Code (Direkteingabe beim Live-Scouting).

Unterstützt den Main Code plus optionale Zonenangaben:

    [*|a]<Nummer 1-2stellig><Skill><Typ?><Bewertung?><Startzone?><Endzone?><Subzone?>

Beispiele: ``5SQ=``, ``a7AT#``, ``*08RQ#``, ``14AH+45``, ``14AH+45B``.
Vollständige Referenz: ../recherche/Data_Volley_4_Funktionsanalyse.md, Abschnitt 3.
Die Subzone (A–D) verfeinert die Zielzone auf 1,5×1,5 m und ist damit die
eigentliche Richtungsangabe (Startzone → Zielzone+Subzone) — siehe Abschnitt 3.2
der Recherche sowie `frontend/src/components/VolleyballCourt.vue`. Kombinations-/
Setter-Call-Codes (Advanced-Code-Feld 7–8) werden hier bewusst noch nicht
unterstützt (mehrdeutig in der kompakten Direkteingabe ohne weiteres Trennzeichen);
das folgt mit dem Klickpfad-System (Roadmap 2.5). Unbekannte Restzeichen bleiben
im Rohcode erhalten und werden mitgespeichert.
"""

import re
from dataclasses import dataclass
from typing import Any

SKILLS = {
    "S": "Serve",
    "R": "Reception",
    "A": "Attack",
    "B": "Block",
    "D": "Dig",
    "E": "Set",
    "F": "Freeball",
}
HIT_TYPES = set("HMQTUNO")
EVALUATIONS = set("#+!-/=")
SUBZONES = set("ABCD")

_MAIN_CODE = re.compile(
    r"""^
    (?P<side>[*a])?
    (?P<number>\d{1,2})
    (?P<skill>[SRABDEF])
    (?P<hit_type>[HMQTUNO])?
    (?P<evaluation>[\#\+\!\-\/\=])?
    (?P<start_zone>[1-9])?
    (?P<end_zone>[1-9])?
    (?P<subzone>[A-D])?
    (?P<rest>.*)
    $""",
    re.VERBOSE,
)


class ScoutCodeError(ValueError):
    """Der eingegebene Code entspricht nicht dem Data-Volley-Main-Code."""


@dataclass(frozen=True)
class ParsedAction:
    raw_code: str
    side: str  # "home" | "away"
    player_number: int
    skill: str
    hit_type: str | None
    evaluation: str | None
    start_zone: int | None
    end_zone: int | None
    subzone: str | None  # A-D, verfeinert die Zielzone (Richtung)


def parse_action(code: str, default_side: str = "home") -> ParsedAction:
    code = code.strip()
    match = _MAIN_CODE.match(code.upper().replace("A", "a", 1) if code[:1] == "a" else code.upper())
    if not match or (match.group("rest") and not match.group("evaluation")):
        raise ScoutCodeError(f"Ungültiger Scout-Code: {code!r}")
    # Subzone ist nur sinnvoll, wenn auch eine Zielzone erfasst wurde.
    if match.group("subzone") and not match.group("end_zone"):
        raise ScoutCodeError(f"Ungültiger Scout-Code: {code!r} (Subzone ohne Zielzone).")

    side_char = match.group("side")
    if side_char == "a":
        side = "away"
    elif side_char == "*":
        side = "home"
    else:
        side = default_side

    return ParsedAction(
        raw_code=code,
        side=side,
        player_number=int(match.group("number")),
        skill=match.group("skill"),
        hit_type=match.group("hit_type"),
        evaluation=match.group("evaluation"),
        start_zone=int(z) if (z := match.group("start_zone")) else None,
        end_zone=int(z) if (z := match.group("end_zone")) else None,
        subzone=match.group("subzone"),
    )


def parse_action_lenient(code: str, default_side: str = "home") -> dict[str, Any]:
    """Like `parse_action`, but never raises.

    The live-scouting text field is meant to work like a plain text input —
    it should assist, not block (user feedback: a scout typing fast can't
    have a single malformed code reject the whole rally, since that would
    also lose the point/score for that rally). Codes that don't match the
    main-code grammar are kept as-is: `raw_code` preserves exactly what was
    typed, `side` is still guessed from a `*`/`a` prefix, everything else is
    `None` — correctable later from the history log instead of being
    rejected up front.
    """
    try:
        return parse_action(code, default_side).__dict__
    except (ScoutCodeError, IndexError):
        return {
            "raw_code": code.strip(),
            "side": _guess_side(code, default_side),
            "player_number": None,
            "skill": None,
            "hit_type": None,
            "evaluation": None,
            "start_zone": None,
            "end_zone": None,
            "subzone": None,
        }


def _guess_side(code: str, default_side: str) -> str:
    prefix = code.strip()[:1]
    if prefix == "a":
        return "away"
    if prefix == "*":
        return "home"
    return default_side
