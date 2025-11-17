"""Integration helpers for Google's Gemini multimodal API."""
from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional

from backend.config import settings
from backend.models.session import Argument

try:  # pragma: no cover - optional dependency during tests
    import google.generativeai as genai
except ImportError:  # pragma: no cover - fallback when package missing
    genai = None  # type: ignore[assignment]

_logger = logging.getLogger(__name__)
_CONFIGURED = False


class GeminiError(RuntimeError):
    """Raised when the Gemini API call fails."""


def _configure_if_needed() -> bool:
    global _CONFIGURED
    if genai is None or not settings.gemini_api_key:
        return False
    if not _CONFIGURED:
        genai.configure(api_key=settings.gemini_api_key)
        _CONFIGURED = True
    return True


def generate_topics(context: Optional[Dict[str, str]] = None) -> List[str]:
    """Ask Gemini to propose three balanced debate topics."""

    if _configure_if_needed():
        prompt = (
            "You are helping set up a friendly debate. Suggest three neutral,"
            " contemporary topics that work well for a timed debate."
            " Avoid controversial or harmful content. Respond as a JSON list of"
            " short topic strings."
        )
        if context and context.get("mode") == "invite" and context.get("hint"):
            prompt += f" The host hinted the debate should involve: {context['hint']}."
        try:
            model = genai.GenerativeModel(settings.gemini_model)
            response = model.generate_content(prompt)
            if response and response.text:
                topics = _extract_list(response.text)
                if topics:
                    return topics
        except Exception as exc:  # pragma: no cover - network call
            _logger.exception("Gemini topic generation failed: %s", exc)
            raise GeminiError("Gemini topic generation failed") from exc

    # Fallback topics when the API is not available
    _logger.warning("Using fallback topics because Gemini is unavailable")
    return [
        "Should remote teams adopt four-day work weeks?",
        "Is universal basic income a sustainable policy?",
        "Do large language models improve developer productivity?",
    ]


def score_arguments(
    transcript: Iterable[Argument],
    topic: str,
    session_metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    """Obtain argument-level scores and an overall winner from Gemini."""

    arguments_payload = [
        {
            "turn": argument.turn_index,
            "role": argument.speaker_role.value,
            "speaker": argument.speaker_name,
            "content": argument.content,
            "time_taken": argument.time_taken_seconds,
        }
        for argument in transcript
    ]

    if _configure_if_needed():
        prompt = (
            "You are an impartial debate adjudicator. Rate each argument from 1"
            " to 10 considering clarity, evidence, and responsiveness."
            " Provide a JSON object with keys: 'per_argument' (list with turn,"
            " role, score, feedback), 'overall' (object with role->score),"
            " 'winner' (role string or 'tie'), and 'summary' (short rationale)."
            f" The debate topic was: {topic!r}."
        )
        if session_metadata:
            prompt += f" Additional context: {session_metadata}."
        try:
            model = genai.GenerativeModel(settings.gemini_model)
            response = model.generate_content(
                [
                    {"text": prompt},
                    {"text": "Transcript:"},
                    {"text": str(arguments_payload)},
                ]
            )
            if response and response.text:
                parsed = _extract_json(response.text)
                if isinstance(parsed, dict):
                    return parsed
        except Exception as exc:  # pragma: no cover - network call
            _logger.exception("Gemini scoring failed: %s", exc)
            raise GeminiError("Gemini scoring failed") from exc

    # Fallback heuristic scoring when Gemini is unavailable
    _logger.warning("Using heuristic debate scoring due to missing Gemini")
    totals: Dict[str, float] = {}
    per_argument: List[Dict[str, object]] = []
    for argument in arguments_payload:
        role = argument["role"]
        base_score = 5.0
        length_bonus = min(len(argument["content"]) / 300, 3)
        score = base_score + length_bonus
        totals[role] = totals.get(role, 0.0) + score
        per_argument.append(
            {
                "turn": argument["turn"],
                "role": role,
                "score": round(score, 2),
                "feedback": "Heuristic score assigned (Gemini offline).",
            }
        )
    winner = max(totals, key=totals.get) if totals else "tie"
    return {
        "per_argument": per_argument,
        "overall": {role: round(score, 2) for role, score in totals.items()},
        "winner": winner,
        "summary": "Scores generated via fallback heuristic.",
    }


def _extract_list(text: str) -> List[str]:
    text = text.strip()
    if text.startswith("["):
        parsed = _extract_json(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()][:3]
    separators = ["\n", "-", "•", "*"]
    for sep in separators:
        if sep in text:
            parts = [p.strip(" -*•") for p in text.split(sep) if p.strip(" -*•")]
            if len(parts) >= 3:
                return parts[:3]
    return [text]


def _extract_json(text: str) -> Optional[object]:
    import json

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Sometimes Gemini wraps JSON in code fences
        if "```" in text:
            snippet = text.split("```", 2)[1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                return None
        return None
