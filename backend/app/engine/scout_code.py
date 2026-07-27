"""Parser für den Data-Volley-Main-Code (Direkteingabe beim Live-Scouting).

Unterstützt den Main Code plus optionale Zonenangaben:

    [*|a]<Nummer 1-2stellig><Skill><Typ?><Bewertung?><Startzone?><Endzone?>

Beispiele: ``5SQ=``, ``a7AT#``, ``*08RQ#``, ``14AH+45``.
Vollständige Referenz: ../recherche/Data_Volley_4_Funktionsanalyse.md, Abschnitt 3.
Advanced-/Extended-Anteile (Kombinationen, Setter-Calls, Subzonen) folgen später;
unbekannte Restzeichen bleiben im Rohcode erhalten und werden mitgespeichert.
"""

import re
from dataclasses import dataclass

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

_MAIN_CODE = re.compile(
    r"""^
    (?P<side>[*a])?
    (?P<number>\d{1,2})
    (?P<skill>[SRABDEF])
    (?P<hit_type>[HMQTUNO])?
    (?P<evaluation>[\#\+\!\-\/\=])?
    (?P<start_zone>[1-9])?
    (?P<end_zone>[1-9])?
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


def parse_action(code: str, default_side: str = "home") -> ParsedAction:
    code = code.strip()
    match = _MAIN_CODE.match(code.upper().replace("A", "a", 1) if code[:1] == "a" else code.upper())
    if not match or (match.group("rest") and not match.group("evaluation")):
        raise ScoutCodeError(f"Ungültiger Scout-Code: {code!r}")

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
    )
