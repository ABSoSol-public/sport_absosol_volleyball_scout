"""Parser für DataVolley-Scoutdateien (.dvw).

Feldlayout nach `docs/DVW-FORMAT.md` (an echten Dateien verifiziert):
Sektionen `[3XXX]`, Semikolon-Felder, `~`-Padding im Code-Feld auf feste
Positionen (Main 1–6, Cmb 7–8, Target 9, Startzone 10, Endzone 11, Subzone 12,
Extended 13–15, Custom 16–20). Legacy-Dateien sind häufig CP1252-kodiert.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime

SECTION_RE = re.compile(r"^\[3([A-Z-]+)\]$")
MAIN_CODE_RE = re.compile(
    r"^(?P<side>[*a])(?P<number>\d{2})(?P<skill>[SRABDEF])"
    r"(?P<hit_type>[HMQTUNO~])?(?P<evaluation>[#+!\-/=~])?(?P<rest>.*)$"
)
POINT_RE = re.compile(r"^(?P<side>[*a])p(?P<home>\d+):(?P<away>\d+)$")


class DvwParseError(ValueError):
    pass


@dataclass
class DvwTeam:
    code: str
    name: str
    sets_won: int
    coach: str = ""


@dataclass
class DvwPlayer:
    number: int
    player_code: str
    last_name: str
    first_name: str
    is_libero: bool = False


@dataclass
class DvwSet:
    number: int
    final_score: tuple[int, int] | None
    duration_minutes: int | None


@dataclass
class DvwScoutRow:
    raw_code: str
    set_number: int
    point_phase: str = ""
    # Nur bei Spieler-Aktionscodes gefüllt:
    side: str | None = None  # home|away
    player_number: int | None = None
    skill: str | None = None
    hit_type: str | None = None
    evaluation: str | None = None
    start_zone: int | None = None
    end_zone: int | None = None
    # Nur bei Punktcodes gefüllt:
    point_side: str | None = None
    home_score: int | None = None
    away_score: int | None = None


@dataclass
class DvwFile:
    match_date: date | None
    competition: str
    home_team: DvwTeam
    away_team: DvwTeam
    home_players: list[DvwPlayer] = field(default_factory=list)
    away_players: list[DvwPlayer] = field(default_factory=list)
    sets: list[DvwSet] = field(default_factory=list)
    scout_rows: list[DvwScoutRow] = field(default_factory=list)


def _decode(content: bytes) -> str:
    for encoding in ("utf-8", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("latin-1")


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip("﻿").rstrip()
        match = SECTION_RE.match(line)
        if match:
            current = sections.setdefault(match.group(1), [])
        elif current is not None and line:
            current.append(line)
    return sections


def _clean(value: str) -> str | None:
    value = value.strip()
    return value if value and value != "~" else None


def _parse_team(line: str) -> DvwTeam:
    fields = line.split(";")
    return DvwTeam(
        code=(fields[0].strip() or "?")[:8],
        name=fields[1].strip() if len(fields) > 1 else "?",
        sets_won=int(fields[2]) if len(fields) > 2 and fields[2].strip().isdigit() else 0,
        coach=fields[3].strip() if len(fields) > 3 else "",
    )


def _parse_player(line: str) -> DvwPlayer | None:
    fields = line.split(";")
    if len(fields) < 11 or not fields[1].strip().isdigit():
        return None
    return DvwPlayer(
        number=int(fields[1]),
        player_code=fields[8].strip(),
        last_name=fields[9].strip() or "?",
        first_name=fields[10].strip(),
        is_libero=len(fields) > 12 and fields[12].strip().upper() == "L",
    )


def _parse_code(raw: str, set_number: int, point_phase: str) -> DvwScoutRow:
    row = DvwScoutRow(raw_code=raw, set_number=set_number, point_phase=point_phase)

    point = POINT_RE.match(raw)
    if point:
        row.point_side = "home" if point.group("side") == "*" else "away"
        row.home_score = int(point.group("home"))
        row.away_score = int(point.group("away"))
        return row

    action = MAIN_CODE_RE.match(raw)
    if action:
        row.side = "home" if action.group("side") == "*" else "away"
        row.player_number = int(action.group("number"))
        row.skill = action.group("skill")
        row.hit_type = _clean(action.group("hit_type") or "")
        row.evaluation = _clean(action.group("evaluation") or "")
        # Positionsfeste Fortsetzung: Cmb(2) Target(1) Start(1) End(1) Sub(1) …
        rest = action.group("rest")
        start = _clean(rest[3]) if len(rest) > 3 else None
        end = _clean(rest[4]) if len(rest) > 4 else None
        row.start_zone = int(start) if start and start.isdigit() else None
        row.end_zone = int(end) if end and end.isdigit() else None
    return row


def parse_dvw(content: bytes) -> DvwFile:
    sections = _sections(_decode(content))
    if "SCOUT" not in sections or "TEAMS" not in sections:
        raise DvwParseError("Keine gültige DVW-Datei (Sektionen [3TEAMS]/[3SCOUT] fehlen).")
    if len(sections["TEAMS"]) < 2:
        raise DvwParseError("Sektion [3TEAMS] muss zwei Teams enthalten.")

    match_date: date | None = None
    competition = ""
    if sections.get("MATCH"):
        match_fields = sections["MATCH"][0].split(";")
        try:
            match_date = datetime.strptime(match_fields[0].strip(), "%d/%m/%Y").date()
        except (ValueError, IndexError):
            match_date = None
        if len(match_fields) > 3:
            competition = match_fields[3].strip()

    result = DvwFile(
        match_date=match_date,
        competition=competition,
        home_team=_parse_team(sections["TEAMS"][0]),
        away_team=_parse_team(sections["TEAMS"][1]),
    )

    for key, target in (("PLAYERS-H", result.home_players), ("PLAYERS-V", result.away_players)):
        for line in sections.get(key, []):
            player = _parse_player(line)
            if player:
                target.append(player)

    for number, line in enumerate(sections.get("SET", []), start=1):
        fields = line.split(";")
        final = None
        if len(fields) > 4 and "-" in fields[4]:
            left, _, right = fields[4].partition("-")
            if left.strip().isdigit() and right.strip().isdigit():
                final = (int(left), int(right))
        duration = int(fields[5]) if len(fields) > 5 and fields[5].strip().isdigit() else None
        result.sets.append(DvwSet(number=number, final_score=final, duration_minutes=duration))

    for line in sections["SCOUT"]:
        fields = line.split(";")
        raw = fields[0].strip()
        if not raw or ">LUp" in raw:
            continue
        set_number = (
            int(fields[8]) if len(fields) > 8 and fields[8].strip().isdigit() else 1
        )
        point_phase = fields[1].strip() if len(fields) > 1 else ""
        result.scout_rows.append(_parse_code(raw, set_number, point_phase))

    return result
