"""REST API routes for session management and utilities."""
from __future__ import annotations

import io
from typing import Any, Dict

from flask import Blueprint, Response, jsonify, request, send_file

from backend.config import settings
from backend.models.session import (
    DebateSession,
    SessionStatus,
    session_registry,
)
from backend.services import gemini, judge, pdf_export
from backend.utils.validators import ValidationError

api_bp = Blueprint("api", __name__)


def _serialize_session(session: DebateSession) -> Dict[str, Any]:
    return {
        "sessionId": session.session_id,
        "inviteCode": session.invite_code,
        "status": session.status.value,
        "topicOptions": session.topic_options,
        "topicRefreshes": session.topic_refreshes,
        "topicRefreshLimit": settings.topic_refresh_limit,
        "chosenTopic": session.chosen_topic,
        "currentTurn": session.current_turn.value if session.current_turn else None,
        "participants": {
            role.value: {
                "name": participant.name,
                "connected": participant.connected,
                "timeSpent": participant.time_spent_seconds,
                "vetoedTopic": participant.vetoed_topic,
                "warnings": participant.warnings,
            }
            for role, participant in session.participants.items()
        },
        "transcript": [
            {
                "turn": argument.turn_index,
                "role": argument.speaker_role.value,
                "speaker": argument.speaker_name,
                "content": argument.content,
                "timeTaken": argument.time_taken_seconds,
                "timestamp": argument.created_at.isoformat(),
            }
            for argument in session.transcript
        ],
        "result": _serialize_result(session.result) if session.result else None,
        "metadata": session.metadata,
        "maxWarnings": settings.max_warnings,
    }


def _serialize_result(result) -> Dict[str, Any]:
    return {
        "winner": result.winner_role.value if result.winner_role else "tie",
        "overall": {role.value: score for role, score in result.overall_score.items()},
        "perArgument": result.per_argument_scores,
        "rationale": result.rationale,
        "flagged": result.flagged_for_review,
        "review": result.review,
    }


@api_bp.post("/sessions/create")
def create_invite_session() -> Response:
    payload = request.get_json(force=True) or {}
    name = payload.get("name", "Host")
    session = session_registry.create_invite_session(name)
    return jsonify(_serialize_session(session)), 201


@api_bp.post("/sessions/join/random")
def join_random_session() -> Response:
    payload = request.get_json(force=True) or {}
    name = payload.get("name", "Player")
    session = session_registry.join_random_match(name)
    status_code = 200 if len(session.participants) == 2 else 202
    return jsonify(_serialize_session(session)), status_code


@api_bp.post("/sessions/join/invite")
def join_invite() -> Response:
    payload = request.get_json(force=True) or {}
    code = payload.get("code")
    name = payload.get("name", "Guest")
    if not code:
        return jsonify({"error": "Invite code required"}), 400
    try:
        session = session_registry.join_invite_session(code.upper(), name)
    except KeyError:
        return jsonify({"error": "Session not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify(_serialize_session(session)), 200


@api_bp.get("/sessions/<session_id>")
def get_session(session_id: str) -> Response:
    try:
        session = session_registry.get(session_id)
    except KeyError:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(_serialize_session(session))


@api_bp.get("/topics/<session_id>")
def get_topics(session_id: str) -> Response:
    try:
        session = session_registry.get(session_id)
    except KeyError:
        return jsonify({"error": "Session not found"}), 404
    refresh_arg = (request.args.get("refresh") or "").strip().lower()
    wants_refresh = refresh_arg in {"1", "true", "yes"}
    refresh_limit = settings.topic_refresh_limit
    if wants_refresh and session.topic_refreshes >= refresh_limit:
        return (
            jsonify({"error": "Topics can only be refreshed once per session."}),
            429,
        )
    if session.topic_options and not wants_refresh:
        return jsonify(
            {
                "topics": session.topic_options,
                "refreshesUsed": session.topic_refreshes,
                "refreshLimit": refresh_limit,
            }
        )
    topics = gemini.generate_topics(session.metadata)
    session_registry.set_topics(session_id, topics, refreshed=wants_refresh)
    session = session_registry.get(session_id)
    return jsonify(
        {
            "topics": topics,
            "refreshesUsed": session.topic_refreshes,
            "refreshLimit": refresh_limit,
        }
    )


@api_bp.post("/sessions/<session_id>/topic")
def select_topic(session_id: str) -> Response:
    payload = request.get_json(force=True) or {}
    topic = payload.get("topic")
    if not topic:
        return jsonify({"error": "Topic required"}), 400
    try:
        session = session_registry.get(session_id)
        if session.custom_topic_allowed and payload.get("custom", False):
            chosen = topic
        else:
            if topic not in session.topic_options:
                raise ValidationError("Topic not in list")
            chosen = topic
        session = session_registry.select_topic(session_id, chosen)
    except (KeyError, ValidationError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_serialize_session(session))


@api_bp.post("/sessions/<session_id>/finish")
def finish_session(session_id: str) -> Response:
    try:
        session = session_registry.get(session_id)
    except KeyError:
        return jsonify({"error": "Session not found"}), 404
    if session.status != SessionStatus.FINISHED:
        result = judge.judge_session(session)
        session_registry.complete_session(session_id, result)
    session = session_registry.get(session_id)
    return jsonify(_serialize_session(session)), 200


@api_bp.get("/export/<session_id>")
def export_pdf(session_id: str) -> Response:
    try:
        session = session_registry.get(session_id)
    except KeyError:
        return jsonify({"error": "Session not found"}), 404
    if not session.result:
        result = judge.judge_session(session)
        session_registry.complete_session(session_id, result)
    pdf_bytes = pdf_export.render_pdf(session, session.result)  # type: ignore[arg-type]
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"debate-{session.session_id}.pdf",
    )
