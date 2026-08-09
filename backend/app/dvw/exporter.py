"""DVW-Export: Rückweg vom Domänenmodell zum DataVolley-Scoutdatei-Format.

Unterstützt beide Datenquellen-Stränge gleichwertig (Nutzerwunsch, 2026-08-09:
"Reexport ist auch wichtig, beides"):
- **Analyse-Strang** (`match_sets`/`rallies`/`scout_actions`) — z. B. Reexport
  einer zuvor per DVW importierten Datei, ggf. nach Korrekturen in der App.
- **Live-Strang** (`live_events`) — per Replay über `MatchEngine`, dieselbe
  inkrementelle Punktestand-Herleitung wie `GET .../live/history`
  (`app/api/live.py`), hier fürs `[3SCOUT]`-Zeilenformat statt für die
  Historylog-Tabelle.

Beide Stränge münden in dieselbe `ExportMatch`-Zwischendarstellung, die
`render_dvw` dann in Text umsetzt — ein Renderer für beide Quellen.

**Codes werden aus den einzelnen Feldern neu zusammengesetzt, nicht als
Rohtext wiederverwendet** — bewusste Designentscheidung, nachdem der erste
Anlauf (Rohtext + nur Präfix ergänzen) beim Testen zwei echte Bugs zeigte:
(1) die *strikte* DVW-Grammatik (`app/dvw/parser.py`, `MAIN_CODE_RE`)
verlangt eine zweistellige, nullgepolsterte Spielernummer (`\\d{2}`) —
die *nachsichtige* Live-Grammatik erlaubt aber einstellige Nummern ohne
Polsterung; unveränderter Rohtext-Reexport eines einstelligen Codes wie
`5SQ-` wäre beim Reimport nicht mehr parsebar gewesen. (2) Die DVW-
Cmb/Target/Zonen-Suffix-Felder sind **positionsfest** (siehe
`_parse_code` in `parser.py`), Start-/Endzone lassen sich nicht einfach an
den Hauptcode anhängen, ohne die (bei Live-Aktionen nicht vorhandenen)
Cmb-/Target-Platzhalter davor. Ein Aufschlag-Annahme-Compound-Code
(`.`-Trenner) wird dabei bewusst in **zwei eigenständige, gültige**
DVW-Zeilen aufgelöst (Aufschlag + Annahme) statt als unparsebare
Compound-Notation reexportiert zu werden — für andere DataVolley-Tools
sind zwei echte Skill-Zeilen wertvoller als ein Rohstring, den nur diese
App selbst versteht.

**Bekannte Einschränkung**: keine der beiden Domänentabellen trackt eine
volle 6-Spieler-Aufstellung je Ballwechsel (nur die Zuspieler-
Rotationsposition) — die DVW-Felder 14–25 (Spielernummern je Zone) bleiben
deshalb leer statt erfunden, ebenso `>LUp`-Aufstellungs-Deklarationszeilen.
Für nicht geparste (nachsichtige Rohcode-Fallback-)Aktionen ohne Skill kann
kein gültiger Main-Code rekonstruiert werden — die bleiben als präfixierter
Rohtext erhalten und runden beim Reimport ggf. nicht sauber.
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.engine.match_engine import MatchEngine, Rules
from app.models import LiveEvent, Match, MatchSet, Player, Rally, Team

GENERATOR_NAME = "ABSoSol Volleyball Scout"


@dataclass
class ExportAction:
    raw_code: str
    side: str  # home|away
    skill: str | None = None
    player_number: int | None = None
    hit_type: str | None = None
    evaluation: str | None = None
    start_zone: int | None = None
    end_zone: int | None = None
    subzone: str | None = None
    attack_combination: str | None = None
    target_attack: str | None = None
    timestamp: datetime | None = None


@dataclass
class ExportRally:
    set_number: int
    actions: list[ExportAction]
    winner_side: str  # home|away
    home_score_after: int
    away_score_after: int
    home_setter_position: int | None = None
    away_setter_position: int | None = None


@dataclass
class ExportPlayer:
    number: int
    last_name: str
    first_name: str = ""
    is_libero: bool = False


@dataclass
class ExportSet:
    number: int
    home_points: int
    away_points: int
    duration_minutes: int | None = None


@dataclass
class ExportMatch:
    match_date: date
    competition: str
    home_team_code: str
    home_team_name: str
    away_team_code: str
    away_team_name: str
    home_players: list[ExportPlayer] = field(default_factory=list)
    away_players: list[ExportPlayer] = field(default_factory=list)
    sets: list[ExportSet] = field(default_factory=list)
    rallies: list[ExportRally] = field(default_factory=list)


# --------------------------------------------------------------------- render


def render_dvw(export: ExportMatch) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H.%M.%S")
    lines: list[str] = [
        "[3DATAVOLLEYSCOUT]",
        "FILEFORMAT: 2.0",
        f"GENERATOR-DAY: {now}",
        "GENERATOR-IDP: DVW",
        f"GENERATOR-PRG: {GENERATOR_NAME}",
        "GENERATOR-REL: Export 1.0",
        "GENERATOR-VER: Web",
        f"GENERATOR-NAM: {export.competition}",
        f"LASTCHANGE-DAY: {now}",
        "LASTCHANGE-IDP: DVW",
        f"LASTCHANGE-PRG: {GENERATOR_NAME}",
        "LASTCHANGE-REL: Export 1.0",
        "LASTCHANGE-VER: Web",
        "LASTCHANGE-NAM: ",
        "[3MATCH]",
        f"{export.match_date.strftime('%d/%m/%Y')};00.00.00;;{export.competition};;;;;1;1;Z;0;",
        ";;;",
        "[3TEAMS]",
        _team_line(export.home_team_code, export.home_team_name, export.sets, "home"),
        _team_line(export.away_team_code, export.away_team_name, export.sets, "away"),
        "[3MORE]",
        ";;;;;;",
        ";0;0;",
        "[3COMMENTS]",
        "",
        "[3SET]",
    ]
    lines += [_set_line(s) for s in export.sets]
    lines.append("[3PLAYERS-H]")
    lines += [_player_line(p) for p in export.home_players]
    lines.append("[3PLAYERS-V]")
    lines += [_player_line(p) for p in export.away_players]
    lines += ["[3ATTACKCOMBINATION]", "[3SETTERCALL]", "[3WINNINGSYMBOLS]", "[3RESERVE]"]
    lines.append("[3SCOUT]")
    for rally in export.rallies:
        lines += [_scout_action_line(a, rally) for a in rally.actions]
        lines.append(_scout_point_line(rally))
    return "\r\n".join(lines) + "\r\n"


def _team_line(code: str, name: str, sets: list[ExportSet], side: str) -> str:
    won = sum(
        1
        for s in sets
        if (s.home_points > s.away_points if side == "home" else s.away_points > s.home_points)
    )
    return f"{code};{name};{won};;;;"


def _set_line(s: ExportSet) -> str:
    duration = str(s.duration_minutes) if s.duration_minutes is not None else ""
    return f"True;;;;{s.home_points}-{s.away_points};{duration};"


def _player_line(p: ExportPlayer) -> str:
    libero = "L" if p.is_libero else ""
    return f"0;{p.number};1;1;;;;;;{p.last_name};{p.first_name};;{libero};"


def _prefixed_code(raw_code: str, side: str) -> str:
    if raw_code[:1] in ("*", "a"):
        return raw_code
    return ("*" if side == "home" else "a") + raw_code


def _main_code(action: ExportAction) -> str:
    if action.skill is None or action.player_number is None:
        # Nachsichtiger Rohcode-Fallback (nicht geparst) — kein Feld zum
        # Rekonstruieren vorhanden, unverändert (nur präfixiert) übernehmen.
        return _prefixed_code(action.raw_code, action.side)

    prefix = "*" if action.side == "home" else "a"
    number = f"{action.player_number:02d}"
    hit_type = action.hit_type or "~"
    evaluation = action.evaluation or "~"
    cmb = ((action.attack_combination or "") + "~~")[:2]
    target = action.target_attack or "~"
    start = str(action.start_zone) if action.start_zone else "~"
    end = str(action.end_zone) if action.end_zone else "~"
    sub = action.subzone or "~"
    code = f"{prefix}{number}{action.skill}{hit_type}{evaluation}{cmb}{target}{start}{end}{sub}"
    return code.rstrip("~")


def _timestamp_field(ts: datetime | None) -> str:
    return ts.strftime("%H.%M.%S") if ts else ""


def _scout_fields(code: str, timestamp: datetime | None, rally: ExportRally) -> str:
    fields = [
        code,
        "",
        "",
        "",
        "",
        "",
        "",
        _timestamp_field(timestamp),
        str(rally.set_number),
        str(rally.home_setter_position) if rally.home_setter_position else "",
        str(rally.away_setter_position) if rally.away_setter_position else "",
    ]
    return ";".join(fields) + ";"


def _scout_action_line(action: ExportAction, rally: ExportRally) -> str:
    return _scout_fields(_main_code(action), action.timestamp, rally)


def _scout_point_line(rally: ExportRally) -> str:
    prefix = "*" if rally.winner_side == "home" else "a"
    code = f"{prefix}p{rally.home_score_after}:{rally.away_score_after}"
    timestamp = rally.actions[-1].timestamp if rally.actions else None
    return _scout_fields(code, timestamp, rally)


# --------------------------------------------------------------- build: DVW-Import-Strang


def build_export_from_analyse_strang(db: Session, match: Match) -> ExportMatch | None:
    sets = list(
        db.scalars(select(MatchSet).where(MatchSet.match_id == match.id).order_by(MatchSet.number))
    )
    if not sets:
        return None

    home_team = db.get(Team, match.home_team_id)
    away_team = db.get(Team, match.away_team_id)
    set_number_by_id = {s.id: s.number for s in sets}

    rallies_db = list(
        db.scalars(
            select(Rally)
            .join(MatchSet)
            .where(MatchSet.match_id == match.id)
            .options(selectinload(Rally.actions))
            .order_by(MatchSet.number, Rally.number)
        )
    )
    export_rallies = [
        ExportRally(
            set_number=set_number_by_id[rally.set_id],
            actions=[
                ExportAction(
                    raw_code=a.raw_code,
                    side=a.side,
                    skill=a.skill,
                    player_number=a.player_number,
                    hit_type=a.hit_type,
                    evaluation=a.evaluation,
                    start_zone=a.start_zone,
                    end_zone=a.end_zone,
                    subzone=a.subzone,
                    attack_combination=a.attack_combination,
                    target_attack=a.target_attack,
                    timestamp=a.created_at,
                )
                for a in rally.actions
            ],
            winner_side=rally.winner_side,
            home_score_after=rally.home_score_after,
            away_score_after=rally.away_score_after,
            home_setter_position=rally.home_setter_position,
            away_setter_position=rally.away_setter_position,
        )
        for rally in rallies_db
    ]

    return ExportMatch(
        match_date=match.match_date,
        competition=match.competition,
        home_team_code=home_team.code,
        home_team_name=home_team.name,
        away_team_code=away_team.code,
        away_team_name=away_team.name,
        home_players=_export_players(home_team.players),
        away_players=_export_players(away_team.players),
        sets=[
            ExportSet(
                number=s.number,
                home_points=s.home_points,
                away_points=s.away_points,
                duration_minutes=s.duration_minutes,
            )
            for s in sets
        ],
        rallies=export_rallies,
    )


def _export_players(players: list[Player]) -> list[ExportPlayer]:
    return [
        ExportPlayer(
            number=p.number, last_name=p.last_name, first_name=p.first_name, is_libero=p.is_libero
        )
        for p in players
    ]


# ----------------------------------------------------------------- build: Live-Strang


def _setter_zone(roster: list[Player], lineup: list[int]) -> int | None:
    """Portiert dieselbe Regel wie `setterZone()` in `RotationCourt.vue`:
    Zone des Referenz-Zuspielers, falls der auf dem Feld steht, sonst
    Fallback auf den tatsächlich aufgestellten Zuspieler.
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


def build_export_from_live_events(db: Session, match: Match) -> ExportMatch | None:
    events = list(
        db.scalars(select(LiveEvent).where(LiveEvent.match_id == match.id).order_by(LiveEvent.seq))
    )
    if not events:
        return None

    home_team = db.get(Team, match.home_team_id)
    away_team = db.get(Team, match.away_team_id)
    home_roster = list(db.scalars(select(Player).where(Player.team_id == home_team.id)))
    away_roster = list(db.scalars(select(Player).where(Player.team_id == away_team.id)))

    rules = Rules(
        best_of=match.best_of,
        points_per_set=match.points_per_set,
        tiebreak_points=match.tiebreak_points,
        substitutions_per_set=match.substitutions_per_set,
        timeouts_per_set=match.timeouts_per_set,
    )
    engine = MatchEngine(rules)
    export_rallies: list[ExportRally] = []

    for event in events:
        if event.event_type == "rally":
            # Aufstellung/Satznummer *vor* dieser Aktion — die Rotation, unter
            # der der Ballwechsel tatsächlich gespielt wurde (`apply_event`
            # rotiert bei Side-Out sofort weiter).
            current = engine.current_set
            lineup_home = list(current.lineups["home"]) if current else []
            lineup_away = list(current.lineups["away"]) if current else []
            set_number = current.number if current else 1

        engine.apply_event(event.event_type, event.payload)

        if event.event_type != "rally":
            continue

        actions = [
            ExportAction(
                raw_code=a["raw_code"],
                side=a["side"],
                skill=a.get("skill"),
                player_number=a.get("player_number"),
                hit_type=a.get("hit_type"),
                evaluation=a.get("evaluation"),
                start_zone=a.get("start_zone"),
                end_zone=a.get("end_zone"),
                subzone=a.get("subzone"),
                timestamp=event.created_at,
            )
            for a in event.payload.get("actions", [])
        ]

        # `current_set` bleibt nach `_on_rally` dieselbe Instanz (auch wenn der
        # Satz dadurch gerade zu Ende ging, nur mit `finished=True`) — der
        # Punktestand direkt danach ist also immer hier abzulesen.
        current_now = engine.current_set
        home_after = current_now.points["home"] if current_now else 0
        away_after = current_now.points["away"] if current_now else 0
        export_rallies.append(
            ExportRally(
                set_number=set_number,
                actions=actions,
                winner_side=event.payload["winner"],
                home_score_after=home_after,
                away_score_after=away_after,
                home_setter_position=_setter_zone(home_roster, lineup_home),
                away_setter_position=_setter_zone(away_roster, lineup_away),
            )
        )

    finished_sets = [
        ExportSet(number=s.number, home_points=s.points["home"], away_points=s.points["away"])
        for s in engine.set_history
    ]

    return ExportMatch(
        match_date=match.match_date,
        competition=match.competition,
        home_team_code=home_team.code,
        home_team_name=home_team.name,
        away_team_code=away_team.code,
        away_team_name=away_team.name,
        home_players=_export_players(home_roster),
        away_players=_export_players(away_roster),
        sets=finished_sets,
        rallies=export_rallies,
    )


def build_export_match(db: Session, match: Match) -> ExportMatch | None:
    """Wählt den passenden Strang: ein Match hat aktuell nie beide gleichzeitig
    befüllt (die Zusammenführung folgt erst mit Roadmap 2.7) — Analyse-Strang
    hat Vorrang, falls doch einmal beides vorläge."""
    return build_export_from_analyse_strang(db, match) or build_export_from_live_events(db, match)
