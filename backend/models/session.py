"""Data models and in-memory registry for debate sessions."""
from __future__ import annotations

import secrets
import string
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from backend.config import settings


class SessionStatus(str, Enum):
    """Lifecycle phases for a debate session."""

    LOBBY = "lobby"
    VETO = "veto"
    COIN_TOSS = "coin_toss"
    DEBATING = "debating"
    FINISHED = "finished"


class ParticipantRole(str, Enum):
    """Enumerated speaker roles."""

    PROPONENT = "pro"
    OPPONENT = "con"


@dataclass
class Participant:
    """Represents a human participant connected to the debate."""

    session_id: str
    socket_id: Optional[str]
    name: str
    role: ParticipantRole
    joined_at: datetime = field(default_factory=datetime.utcnow)
    connected: bool = True
    vetoed_topic: Optional[str] = None
    time_spent_seconds: int = 0


@dataclass
class Argument:
    """Single argument or turn of the debate."""

    speaker_role: ParticipantRole
    speaker_name: str
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    turn_index: int = 0
    time_taken_seconds: int = 0
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class SessionResult:
    """Stores the judged outcome of a debate."""

    winner_role: Optional[ParticipantRole] = None
    overall_score: Dict[ParticipantRole, float] = field(default_factory=dict)
    per_argument_scores: List[Dict[str, object]] = field(default_factory=list)
    rationale: str = ""
    flagged_for_review: bool = False


@dataclass
class DebateSession:
    """Aggregate state for an active debate session."""

    session_id: str
    invite_code: str
    status: SessionStatus = SessionStatus.LOBBY
    created_at: datetime = field(default_factory=datetime.utcnow)
    participants: Dict[ParticipantRole, Participant] = field(default_factory=dict)
    topic_options: List[str] = field(default_factory=list)
    chosen_topic: Optional[str] = None
    transcript: List[Argument] = field(default_factory=list)
    current_turn: Optional[ParticipantRole] = None
    total_elapsed_seconds: int = 0
    max_turns: int = settings.max_turns
    per_turn_limit: int = settings.default_turn_seconds
    total_time_limit: int = settings.default_total_seconds
    result: Optional[SessionResult] = None
    custom_topic_allowed: bool = False
    metadata: Dict[str, str] = field(default_factory=dict)

    def next_role(self) -> ParticipantRole:
        if self.current_turn == ParticipantRole.PROPONENT:
            return ParticipantRole.OPPONENT
        return ParticipantRole.PROPONENT

    def record_argument(self, role: ParticipantRole, content: str, time_taken: int) -> Argument:
        argument = Argument(
            speaker_role=role,
            speaker_name=self.participants[role].name,
            content=content,
            turn_index=len(self.transcript),
            time_taken_seconds=time_taken,
        )
        self.transcript.append(argument)
        self.current_turn = self.next_role()
        return argument


class SessionRegistry:
    """In-memory storage and matchmaking for sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, DebateSession] = {}
        self._lock = threading.RLock()
        self._waiting_random: Optional[str] = None

    def _generate_session_id(self) -> str:
        return secrets.token_hex(8)

    def _generate_invite_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(6))

    def create_invite_session(self, host_name: str) -> DebateSession:
        with self._lock:
            session_id = self._generate_session_id()
            session = DebateSession(session_id=session_id, invite_code=self._generate_invite_code())
            session.custom_topic_allowed = True
            session.metadata["mode"] = "invite"
            participant = Participant(
                session_id=session_id,
                socket_id=None,
                name=host_name or "Host",
                role=ParticipantRole.PROPONENT,
            )
            session.participants[ParticipantRole.PROPONENT] = participant
            session.current_turn = ParticipantRole.PROPONENT
            self._sessions[session_id] = session
            return session

    def join_invite_session(self, code: str, participant_name: str) -> DebateSession:
        with self._lock:
            for session in self._sessions.values():
                if session.invite_code == code:
                    if ParticipantRole.OPPONENT in session.participants:
                        raise ValueError("Session already full")
                    participant = Participant(
                        session_id=session.session_id,
                        socket_id=None,
                        name=participant_name or "Guest",
                        role=ParticipantRole.OPPONENT,
                    )
                    session.participants[ParticipantRole.OPPONENT] = participant
                    session.status = SessionStatus.VETO
                    session.metadata["mode"] = "invite"
                    return session
            raise KeyError("Session not found")

    def join_random_match(self, participant_name: str) -> DebateSession:
        with self._lock:
            if self._waiting_random and self._waiting_random in self._sessions:
                session = self._sessions[self._waiting_random]
                self._waiting_random = None
                role = ParticipantRole.OPPONENT
                participant = Participant(
                    session_id=session.session_id,
                    socket_id=None,
                    name=participant_name or "Opponent",
                    role=role,
                )
                session.participants[role] = participant
                session.status = SessionStatus.VETO
                session.metadata["mode"] = "random"
                return session

            session_id = self._generate_session_id()
            session = DebateSession(session_id=session_id, invite_code=self._generate_invite_code())
            session.metadata["mode"] = "random"
            participant = Participant(
                session_id=session_id,
                socket_id=None,
                name=participant_name or "Player",
                role=ParticipantRole.PROPONENT,
            )
            session.participants[ParticipantRole.PROPONENT] = participant
            session.current_turn = ParticipantRole.PROPONENT
            self._sessions[session_id] = session
            self._waiting_random = session_id
            return session

    def get(self, session_id: str) -> DebateSession:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError("Session not found")
            return self._sessions[session_id]

    def all(self) -> List[DebateSession]:
        with self._lock:
            return list(self._sessions.values())

    def set_topics(self, session_id: str, topics: List[str]) -> None:
        with self._lock:
            session = self.get(session_id)
            session.topic_options = topics
            session.status = SessionStatus.VETO

    def select_topic(self, session_id: str, topic: str) -> DebateSession:
        with self._lock:
            session = self.get(session_id)
            session.chosen_topic = topic
            session.status = SessionStatus.COIN_TOSS

            # Ensure we clear any previous toss metadata before assigning new values.
            session.metadata["coinTossCompleted"] = False

            pro_participant = session.participants.get(ParticipantRole.PROPONENT)
            con_participant = session.participants.get(ParticipantRole.OPPONENT)

            assigned_pro = pro_participant
            assigned_con = con_participant

            if pro_participant and con_participant:
                # Randomly decide whether to swap roles between the two debaters.
                if secrets.randbelow(2) == 1:
                    pro_participant.role = ParticipantRole.PROPONENT
                    con_participant.role = ParticipantRole.OPPONENT
                else:
                    pro_participant.role = ParticipantRole.OPPONENT
                    con_participant.role = ParticipantRole.PROPONENT
                    session.participants[ParticipantRole.PROPONENT] = con_participant
                    session.participants[ParticipantRole.OPPONENT] = pro_participant
                assigned_pro = session.participants.get(ParticipantRole.PROPONENT)
                assigned_con = session.participants.get(ParticipantRole.OPPONENT)
            else:
                # If only one participant is connected we still keep existing
                # assignments so they can see the pending result when the
                # opponent joins.
                if pro_participant:
                    pro_participant.role = ParticipantRole.PROPONENT
                if con_participant:
                    con_participant.role = ParticipantRole.OPPONENT

            session.metadata["coinToss"] = {
                "pro": assigned_pro.name if assigned_pro else None,
                "con": assigned_con.name if assigned_con else None,
            }
            session.current_turn = ParticipantRole.PROPONENT
            return session

    def complete_session(self, session_id: str, result: SessionResult) -> DebateSession:
        with self._lock:
            session = self.get(session_id)
            session.result = result
            session.status = SessionStatus.FINISHED
            return session

    def resolve_coin_toss(self, session_id: str) -> DebateSession:
        with self._lock:
            session = self.get(session_id)
            if session.status == SessionStatus.COIN_TOSS:
                session.status = SessionStatus.DEBATING
                session.metadata["coinTossCompleted"] = True
                session.current_turn = ParticipantRole.PROPONENT
            return session


session_registry = SessionRegistry()
