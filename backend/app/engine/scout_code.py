"""Parser für den Data-Volley-Main-Code (Direkteingabe beim Live-Scouting).

Unterstützt den Main Code plus optionale Zonenangaben:

    [*|a]<Nummer 1-2stellig><Skill><Typ?><Bewertung?><Startzone?><Endzone?><Subzone?>

Beispiele: ``5SQ=``, ``a7AT#``, ``*08RQ#``, ``14AH+45``, ``14AH+45B``.
Vollständige Referenz: ../recherche/Data_Volley_4_Funktionsanalyse.md, Abschnitt 3.
Die Subzone (A–D) verfeinert die Zielzone auf 1,5×1,5 m und ist damit die
eigentliche Richtungsangabe (Startzone → Zielzone+Subzone) — siehe Abschnitt 3.2
der Recherche sowie `frontend/src/components/VolleyballCourt.vue`.

Zusätzlich unterstützt `parse_scout_code` den DataVolley-„Compound Code" für
Aufschlag+Annahme (Punkt-Trenner, z. B. ``*3SQ16.11=``) — zerlegt ihn in zwei
verknüpfte Aktionen, siehe die Kommentare bei `_SERVE_EVAL_FROM_RECEPTION`
weiter unten. Andere Compound-Code-Varianten (Angriff+Block, Angriff+Abwehr)
sind bewusst **nicht** unterstützt — dafür fehlen (Stand jetzt) ebenso
präzise, nutzerbestätigte Domänenregeln wie für Aufschlag+Annahme; nicht
erkannte bzw. unbekannte Codes bleiben im Rohcode erhalten und werden
nachsichtig mitgespeichert (`parse_action_lenient`), statt die Eingabe
abzulehnen.
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


def _other_side(side: str) -> str:
    return "away" if side == "home" else "home"


# DataVolley calls the "." notation below a "compound code": it links a serve
# to the paired reception in one token instead of two, e.g. "*3SQ16.11=".
# The serve's own evaluation is never written in this form — it's implied by
# the reception rating (a serve is only as good as the pass it allows), see
# the domain rules this table is built from (user, 2026-08-02):
#   reception "="  (ace / no play)      -> serve "#"
#   reception "-"  (weak pass)          -> serve "+"
#   reception "/"  (uncontrolled pass)  -> serve "/"
#   reception "#" or "+" (good/perfect) -> serve "-" (scout picks which one
#                                          matches what they actually saw)
_SERVE_EVAL_FROM_RECEPTION = {
    "=": "#",
    "-": "+",
    "/": "/",
    "#": "-",
    "+": "-",
}

_RECEIVER_TAIL = re.compile(r"^(?P<number>\d{1,2})(?P<evaluation>[\#\+\!\-\/\=])$")


def parse_scout_code(code: str, default_side: str = "home") -> list[dict[str, Any]]:
    """Parses one user-typed scout-code token, expanding a serve+reception
    compound code into its two linked actions. Never raises.

    Only the serve+reception compound is decomposed here — DataVolley also
    has compound forms for attack+block/attack+dig, but those aren't
    implemented yet (no equally precise, confirmed domain rules for them at
    the time of writing; see docs/ARCHITEKTUR.md). Anything that isn't a
    recognised serve+reception compound falls back to the plain
    `parse_action_lenient` path (a single dict, same as any other code).
    """
    stripped = code.strip()
    if "." in stripped:
        head, _dot, tail = stripped.partition(".")
        tail_match = _RECEIVER_TAIL.match(tail.strip())
        if tail_match:
            try:
                serve = parse_action(head, default_side)
            except (ScoutCodeError, IndexError):
                serve = None
            if serve is not None and serve.skill == "S":
                reception_eval = tail_match.group("evaluation")
                serve_with_eval = ParsedAction(
                    raw_code=stripped,
                    side=serve.side,
                    player_number=serve.player_number,
                    skill=serve.skill,
                    hit_type=serve.hit_type,
                    evaluation=_SERVE_EVAL_FROM_RECEPTION.get(reception_eval),
                    start_zone=serve.start_zone,
                    end_zone=serve.end_zone,
                    subzone=serve.subzone,
                )
                reception = ParsedAction(
                    raw_code=stripped,
                    side=_other_side(serve.side),
                    player_number=int(tail_match.group("number")),
                    skill="R",
                    hit_type=None,
                    evaluation=reception_eval,
                    start_zone=None,
                    end_zone=None,
                    subzone=None,
                )
                return [serve_with_eval.__dict__, reception.__dict__]
    return [parse_action_lenient(code, default_side)]
