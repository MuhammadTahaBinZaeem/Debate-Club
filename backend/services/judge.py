"""Implements the Opus-inspired judging pipeline."""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from models.session import (
    DebateSession,
    ParticipantRole,
    SessionResult,
)
from services import gemini, qdrant
from utils import validators

_logger = logging.getLogger(__name__)


class DebateJudge:
    """Coordinates the Intake → Understand → Decide → Review → Deliver pipeline."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("debate.judge")

    def judge(self, session: DebateSession) -> SessionResult:
        self.logger.info("Starting judging pipeline", extra={"session_id": session.session_id})
        intake_payload = self._intake(session)
        understanding = self._understand(session, intake_payload)
        decision = self._decide(session, understanding)
        reviewed_decision = self._review(session, decision)
        return self._deliver(session, intake_payload, reviewed_decision)

    # Intake
    def _intake(self, session: DebateSession) -> Dict[str, object]:
        validators.ensure_roles_present([role.value for role in session.participants.keys()])
        related_materials: List[dict] = []
        if session.transcript:
            last_argument = session.transcript[-1]
            related_materials = qdrant.search_similar(last_argument.content, limit=5)
        payload = {
            "session_id": session.session_id,
            "topic": session.chosen_topic,
            "transcript": session.transcript,
            "metadata": session.metadata,
            "related_materials": related_materials,
        }
        self.logger.info("Intake complete", extra={"session_id": session.session_id})
        return payload

    # Understand
    def _understand(self, session: DebateSession, intake_payload: Dict[str, object]) -> Dict[str, object]:
        transcript = intake_payload["transcript"]
        topic = intake_payload.get("topic") or "General debate"
        scores = gemini.score_arguments(transcript, topic, session.metadata)
        self.logger.info("Understand step complete", extra={"session_id": session.session_id})
        return {
            "scores": scores,
            "transcript": transcript,
            "topic": topic,
        }

    # Decide
    def _decide(self, session: DebateSession, understanding: Dict[str, object]) -> Dict[str, object]:
        scores = understanding["scores"]
        totals: Dict[str, float] = {role.value: 0.0 for role in session.participants.keys()}
        for entry in scores.get("per_argument", []):
            totals[entry.get("role", "")] = totals.get(entry.get("role", ""), 0.0) + float(entry.get("score", 0))
        missed_turn_penalty = self._calculate_time_penalties(session)
        for role, penalty in missed_turn_penalty.items():
            totals[role] = totals.get(role, 0.0) - penalty
        winner = max(totals.items(), key=lambda item: item[1])[0] if totals else "tie"
        decision = {
            "per_argument": scores.get("per_argument", []),
            "overall": totals,
            "summary": scores.get("summary", ""),
            "winner": winner,
            "raw_scores": scores,
            "penalties": missed_turn_penalty,
            "review": scores.get("review", {}),
        }
        self.logger.info("Decide step complete", extra={"session_id": session.session_id, "winner": winner})
        return decision

    def _calculate_time_penalties(self, session: DebateSession) -> Dict[str, float]:
        penalties: Dict[str, float] = {}
        if session.total_elapsed_seconds > session.total_time_limit:
            overtime = session.total_elapsed_seconds - session.total_time_limit
            penalty = round(overtime / 30.0, 2)
            penalties[ParticipantRole.PROPONENT.value] = penalty / 2
            penalties[ParticipantRole.OPPONENT.value] = penalty / 2
        for role, participant in session.participants.items():
            if participant.time_spent_seconds == 0:
                penalties[role.value] = penalties.get(role.value, 0.0) + 2.5
        return penalties

    # Review
    def _review(self, session: DebateSession, decision: Dict[str, object]) -> Dict[str, object]:
        if not decision["overall"]:
            decision["winner"] = "tie"
            decision["needs_review"] = True
        elif len({round(score, 2) for score in decision["overall"].values()}) == 1:
            decision["needs_review"] = True
        else:
            decision["needs_review"] = False
        self.logger.info(
            "Review step complete",
            extra={"session_id": session.session_id, "needs_review": decision["needs_review"]},
        )
        return decision

    # Deliver
    def _deliver(
        self,
        session: DebateSession,
        intake_payload: Dict[str, object],
        decision: Dict[str, object],
    ) -> SessionResult:
        # Persist embeddings for future retrievals
        qdrant.upsert_arguments(session.session_id, session.transcript)
        winner_role: ParticipantRole | None
        if decision["winner"] in (ParticipantRole.PROPONENT.value, ParticipantRole.OPPONENT.value):
            winner_role = ParticipantRole(decision["winner"])
        else:
            winner_role = None
        overall: Dict[ParticipantRole, float] = {}
        for key, value in decision["overall"].items():
            try:
                overall[ParticipantRole(key)] = float(value)
            except ValueError:
                continue
        result = SessionResult(
            winner_role=winner_role,
            overall_score=overall,
            per_argument_scores=decision.get("per_argument", []),
            rationale=decision.get("summary", ""),
            flagged_for_review=bool(decision.get("needs_review", False)),
            review=decision.get("review", {}),
        )
        self.logger.info(
            "Deliver step complete",
            extra={"session_id": session.session_id, "winner": result.winner_role.value if result.winner_role else "tie"},
        )
        return result


def judge_session(session: DebateSession) -> SessionResult:
    judge = DebateJudge()
    return judge.judge(session)
