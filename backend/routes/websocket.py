"""Socket.IO real-time handlers for the debate experience."""
from __future__ import annotations

import logging
from typing import Dict

from flask import request
from flask_socketio import SocketIO, emit, join_room

from backend.models.session import ParticipantRole, SessionStatus, session_registry
from backend.routes.api import _serialize_session
from backend.services import judge
from backend.utils import timers, validators

logger = logging.getLogger(__name__)

_socket_participants: Dict[str, Dict[str, str]] = {}

timer_manager = timers.timer_manager


def register_socketio_events(socketio: SocketIO) -> None:
    @_socketio_event(socketio, "connect")
    def handle_connect():  # pragma: no cover - network side effect
        logger.info("Socket connected", extra={"sid": request.sid})

    @_socketio_event(socketio, "disconnect")
    def handle_disconnect():  # pragma: no cover - network side effect
        logger.info("Socket disconnected", extra={"sid": request.sid})
        mapping = _socket_participants.pop(request.sid, None)
        if mapping:
            session_id = mapping["session_id"]
            role = ParticipantRole(mapping["role"])
            try:
                session = session_registry.get(session_id)
                if role in session.participants:
                    session.participants[role].connected = False
                    emit("session:update", _serialize_session(session), room=session_id)
            except KeyError:
                pass

    @_socketio_event(socketio, "join_session")
    def join_session(data: Dict[str, str]):
        session_id = data.get("sessionId")
        role = data.get("role")
        if not session_id or not role:
            emit("session:error", {"message": "Session and role required"})
            return
        try:
            session = session_registry.get(session_id)
            participant = session.participants[ParticipantRole(role)]
        except Exception:
            emit("session:error", {"message": "Unable to join session"})
            return
        _socket_participants[request.sid] = {"session_id": session_id, "role": role}
        participant.socket_id = request.sid
        participant.connected = True
        join_room(session_id)
        emit("session:update", _serialize_session(session), room=session_id)
        if session.status == SessionStatus.DEBATING and session.current_turn == ParticipantRole(role):
            _start_turn_timer(socketio, session_id)

    @_socketio_event(socketio, "veto_topic")
    def veto_topic(data: Dict[str, str]):
        mapping = _socket_participants.get(request.sid)
        if not mapping:
            emit("session:error", {"message": "Join the session first"})
            return
        session_id = mapping["session_id"]
        role = ParticipantRole(mapping["role"])
        topic = data.get("topic")
        if not topic:
            emit("session:error", {"message": "Topic required"})
            return
        try:
            session = session_registry.get(session_id)
        except KeyError:
            emit("session:error", {"message": "Session not found"})
            return
        if topic not in session.topic_options:
            emit("session:error", {"message": "Invalid topic"})
            return
        session.participants[role].vetoed_topic = topic
        remaining = [
            option
            for option in session.topic_options
            if option not in {p.vetoed_topic for p in session.participants.values() if p.vetoed_topic}
        ]
        emit("topic:vetoed", {"role": role.value, "topic": topic}, room=session_id)
        if len(remaining) == 1:
            session = session_registry.select_topic(session_id, remaining[0])
            emit("topic:selected", {"topic": remaining[0]}, room=session_id)
            socketio.emit("session:update", _serialize_session(session), room=session_id)
        else:
            emit("session:update", _serialize_session(session), room=session_id)

    @_socketio_event(socketio, "set_custom_topic")
    def set_custom_topic(data: Dict[str, str]):
        mapping = _socket_participants.get(request.sid)
        if not mapping:
            emit("session:error", {"message": "Join the session first"})
            return
        session_id = mapping["session_id"]
        topic = data.get("topic")
        if not topic:
            emit("session:error", {"message": "Topic required"})
            return
        session = session_registry.select_topic(session_id, topic)
        emit("topic:selected", {"topic": topic}, room=session_id)
        socketio.emit("session:update", _serialize_session(session), room=session_id)

    @_socketio_event(socketio, "send_message")
    def send_message(data: Dict[str, str]):
        mapping = _socket_participants.get(request.sid)
        if not mapping:
            emit("session:error", {"message": "Join the session first"})
            return
        session_id = mapping["session_id"]
        role = ParticipantRole(mapping["role"])
        message = data.get("message", "")
        try:
            validators.validate_argument_length(message)
            session = session_registry.get(session_id)
        except (validators.ValidationError, KeyError) as exc:
            emit("session:error", {"message": str(exc)})
            return
        if session.status != SessionStatus.DEBATING:
            emit("session:error", {"message": "Debate not started"})
            return
        if session.current_turn != role:
            emit("session:error", {"message": "Not your turn"})
            return
        elapsed = timer_manager.consume_turn_time(session_id)
        argument = session.record_argument(role, message, elapsed)
        session.participants[role].time_spent_seconds += elapsed
        session.total_elapsed_seconds += elapsed
        emit(
            "message:new",
            {
                "turn": argument.turn_index,
                "role": role.value,
                "speaker": argument.speaker_name,
                "content": argument.content,
                "timeTaken": elapsed,
            },
            room=session_id,
        )
        socketio.emit("session:update", _serialize_session(session), room=session_id)
        if len(session.transcript) >= session.max_turns:
            _finish_debate(socketio, session_id)
        else:
            _start_turn_timer(socketio, session_id)

    @_socketio_event(socketio, "end_debate")
    def end_debate():
        mapping = _socket_participants.get(request.sid)
        if not mapping:
            emit("session:error", {"message": "Join the session first"})
            return
        _finish_debate(socketio, mapping["session_id"])

    @_socketio_event(socketio, "coin_toss_complete")
    def coin_toss_complete():
        mapping = _socket_participants.get(request.sid)
        if not mapping:
            emit("session:error", {"message": "Join the session first"})
            return
        session_id = mapping["session_id"]
        try:
            session = session_registry.get(session_id)
        except KeyError:
            emit("session:error", {"message": "Session not found"})
            return
        previous_status = session.status
        session = session_registry.resolve_coin_toss(session_id)
        socketio.emit("session:update", _serialize_session(session), room=session_id)
        if previous_status != SessionStatus.DEBATING and session.status == SessionStatus.DEBATING:
            _begin_debate(socketio, session_id)


def _start_turn_timer(socketio: SocketIO, session_id: str) -> None:
    try:
        session = session_registry.get(session_id)
    except KeyError:
        return

    def _timeout(sid: str) -> None:
        socketio.start_background_task(_handle_turn_timeout, socketio, sid)

    timer_manager.start_turn_timer(session_id, session.per_turn_limit, _timeout)
    socketio.emit("timer:turn", {"seconds": session.per_turn_limit}, room=session_id)


def _begin_debate(socketio: SocketIO, session_id: str) -> None:
    try:
        session = session_registry.get(session_id)
    except KeyError:
        return
    if session.status != SessionStatus.DEBATING:
        return

    def _total_timeout(sid: str) -> None:
        socketio.start_background_task(_handle_total_timeout, socketio, sid)

    timer_manager.start_total_timer(session_id, session.total_time_limit, _total_timeout)
    _start_turn_timer(socketio, session_id)
    socketio.emit("debate:started", _serialize_session(session), room=session_id)


def _handle_turn_timeout(socketio: SocketIO, session_id: str) -> None:
    try:
        session = session_registry.get(session_id)
    except KeyError:
        return
    role = session.current_turn
    if not role:
        return
    socketio.emit("timer:turnExpired", {"role": role.value}, room=session_id)
    session.participants[role].time_spent_seconds += session.per_turn_limit
    session.total_elapsed_seconds += session.per_turn_limit
    session.current_turn = session.next_role()
    socketio.emit("session:update", _serialize_session(session), room=session_id)
    _start_turn_timer(socketio, session_id)


def _handle_total_timeout(socketio: SocketIO, session_id: str) -> None:
    socketio.emit("timer:totalExpired", {}, room=session_id)
    _finish_debate(socketio, session_id)


def _finish_debate(socketio: SocketIO, session_id: str) -> None:
    timer_manager.cancel_turn_timer(session_id)
    timer_manager.cancel_total_timer(session_id)
    try:
        session = session_registry.get(session_id)
    except KeyError:
        return
    if session.status != SessionStatus.FINISHED:
        result = judge.judge_session(session)
        session_registry.complete_session(session_id, result)
    socketio.emit("debate:finished", _serialize_session(session_registry.get(session_id)), room=session_id)


def _socketio_event(socketio: SocketIO, event: str):
    def decorator(func):
        socketio.on_event(event, func)
        return func

    return decorator
