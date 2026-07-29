"""Domänenmodell: Team, Player, Match, MatchSet, Rally, ScoutAction, LiveEvent.

Die Tabellen `match_sets`, `rallies` und `scout_actions` sind das Ziel-Modell für
Analyse/Import (Roadmap 1.1/1.2). Das Live-Scouting schreibt zunächst ausschließlich
`live_events` (Event-Sourcing: Replay ergibt den Spielstand, Undo = letztes Event löschen);
die Ableitung in Rally-/Action-Zeilen folgt mit dem Analyse-Strang.
"""

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), default="admin")  # admin | viewer
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(120))

    players: Mapped[list["Player"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (UniqueConstraint("team_id", "number", name="uq_player_team_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column()
    last_name: Mapped[str] = mapped_column(String(80))
    first_name: Mapped[str] = mapped_column(String(80), default="")
    position: Mapped[str] = mapped_column(String(20), default="")
    is_libero: Mapped[bool] = mapped_column(default=False)
    # Sonderstellung Jugendspieler (Höherspielrecht/Doppelspielrecht-Regelungen der
    # Landesverbände) — reine Kennzeichnung, keine Regelprüfung in der Engine.
    is_youth_player: Mapped[bool] = mapped_column(default=False)

    team: Mapped[Team] = relationship(back_populates="players")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_date: Mapped[date] = mapped_column(Date)
    competition: Mapped[str] = mapped_column(String(120), default="")
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    # Regulation (Roadmap: Regeln parametrisierbar wie im DV4-Vorbild)
    best_of: Mapped[int] = mapped_column(default=5)
    points_per_set: Mapped[int] = mapped_column(default=25)
    tiebreak_points: Mapped[int] = mapped_column(default=15)
    substitutions_per_set: Mapped[int] = mapped_column(default=6)
    timeouts_per_set: Mapped[int] = mapped_column(default=2)
    status: Mapped[str] = mapped_column(String(16), default="scheduled")  # scheduled|live|finished
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])
    sets: Mapped[list["MatchSet"]] = relationship(
        back_populates="match", cascade="all, delete-orphan", order_by="MatchSet.number"
    )
    events: Mapped[list["LiveEvent"]] = relationship(
        back_populates="match", cascade="all, delete-orphan", order_by="LiveEvent.seq"
    )


class MatchSet(Base):
    __tablename__ = "match_sets"
    __table_args__ = (UniqueConstraint("match_id", "number", name="uq_set_match_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column()
    home_points: Mapped[int] = mapped_column(default=0)
    away_points: Mapped[int] = mapped_column(default=0)
    finished: Mapped[bool] = mapped_column(default=False)
    duration_minutes: Mapped[int | None] = mapped_column(nullable=True)

    match: Mapped[Match] = relationship(back_populates="sets")
    rallies: Mapped[list["Rally"]] = relationship(
        back_populates="match_set", cascade="all, delete-orphan", order_by="Rally.number"
    )


class Rally(Base):
    __tablename__ = "rallies"

    id: Mapped[int] = mapped_column(primary_key=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("match_sets.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column()
    serving_side: Mapped[str] = mapped_column(String(4))  # home|away
    winner_side: Mapped[str] = mapped_column(String(4))  # home|away
    home_score_after: Mapped[int] = mapped_column()
    away_score_after: Mapped[int] = mapped_column()
    # Rotationsposition (1-6) des jeweiligen Zuspielers während dieses Ballwechsels
    # (aus dem DVW-Scout-Strom übernommen, Grundlage für die Rotationsanalyse).
    home_setter_position: Mapped[int | None] = mapped_column(nullable=True)
    away_setter_position: Mapped[int | None] = mapped_column(nullable=True)

    match_set: Mapped[MatchSet] = relationship(back_populates="rallies")
    actions: Mapped[list["ScoutAction"]] = relationship(
        back_populates="rally", cascade="all, delete-orphan", order_by="ScoutAction.seq"
    )


class ScoutAction(Base):
    __tablename__ = "scout_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    rally_id: Mapped[int] = mapped_column(ForeignKey("rallies.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column()
    raw_code: Mapped[str] = mapped_column(String(40))
    side: Mapped[str] = mapped_column(String(4))  # home|away
    player_number: Mapped[int | None] = mapped_column(nullable=True)
    skill: Mapped[str | None] = mapped_column(String(1), nullable=True)  # S R A B D E F
    hit_type: Mapped[str | None] = mapped_column(String(1), nullable=True)  # H M Q T U N O
    evaluation: Mapped[str | None] = mapped_column(String(1), nullable=True)  # # + ! - / =
    start_zone: Mapped[int | None] = mapped_column(nullable=True)
    end_zone: Mapped[int | None] = mapped_column(nullable=True)
    # Advanced Code: Angriffskombination/Setter-Call (Skill A bzw. E), Ziel-Angriff
    # (Front/Center/Back/Pipe/Setter) und Subzone (A-D, Richtungsverfeinerung der
    # Zielzone) — siehe ../recherche/Data_Volley_4_Funktionsanalyse.md Abschnitt 3.2.
    attack_combination: Mapped[str | None] = mapped_column(String(4), nullable=True)
    target_attack: Mapped[str | None] = mapped_column(String(1), nullable=True)
    subzone: Mapped[str | None] = mapped_column(String(1), nullable=True)  # A B C D

    rally: Mapped[Rally] = relationship(back_populates="actions")


class LiveEvent(Base):
    __tablename__ = "live_events"
    __table_args__ = (UniqueConstraint("match_id", "seq", name="uq_event_match_seq"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column()
    event_type: Mapped[str] = mapped_column(String(20))  # start_set|rally|substitution|timeout
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    match: Mapped[Match] = relationship(back_populates="events")
