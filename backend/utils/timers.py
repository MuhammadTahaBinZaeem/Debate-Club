"""Timer utilities for managing debate countdowns."""
from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Optional, Tuple


class TimerManager:
    """Manage per-turn and total debate timers using background threads."""

    def __init__(self) -> None:
        self._turn_timers: Dict[str, Tuple[threading.Timer, float]] = {}
        self._total_timers: Dict[str, Tuple[threading.Timer, float]] = {}
        self._lock = threading.RLock()

    def start_turn_timer(self, session_id: str, seconds: int, callback: Callable[[str], None]) -> None:
        def _fire() -> None:
            callback(session_id)

        with self._lock:
            self.cancel_turn_timer(session_id)
            timer = threading.Timer(seconds, _fire)
            self._turn_timers[session_id] = (timer, time.time())
            timer.start()

    def cancel_turn_timer(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._turn_timers:
                timer, _ = self._turn_timers.pop(session_id)
                timer.cancel()

    def start_total_timer(self, session_id: str, seconds: int, callback: Callable[[str], None]) -> None:
        def _fire() -> None:
            callback(session_id)

        with self._lock:
            self.cancel_total_timer(session_id)
            timer = threading.Timer(seconds, _fire)
            self._total_timers[session_id] = (timer, time.time())
            timer.start()

    def cancel_total_timer(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._total_timers:
                timer, _ = self._total_timers.pop(session_id)
                timer.cancel()

    def consume_turn_time(self, session_id: str) -> int:
        """Return elapsed seconds for the active turn and cancel the timer."""
        with self._lock:
            if session_id not in self._turn_timers:
                return 0
            timer, started_at = self._turn_timers.pop(session_id)
            timer.cancel()
            return int(time.time() - started_at)

    def shutdown(self) -> None:
        for session_id in list(self._turn_timers.keys()):
            self.cancel_turn_timer(session_id)
        for session_id in list(self._total_timers.keys()):
            self.cancel_total_timer(session_id)


timer_manager = TimerManager()
