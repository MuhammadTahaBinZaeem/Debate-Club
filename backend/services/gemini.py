"""Integration helpers for Google's Gemini multimodal API."""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

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
            " role, score, rating, feedback), 'overall' (object with role->score),"
            " 'winner' (role string or 'tie'), 'summary' (short rationale), and"
            " 'review' (object detailing strengths and improvements for each"
            " participant plus an overall assessment)."
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
                    return _normalise_scores(parsed)
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
                "rating": _label_for_score(score),
                "feedback": "Heuristic score assigned (Gemini offline).",
            }
        )
    winner = max(totals, key=totals.get) if totals else "tie"
    return {
        "per_argument": per_argument,
        "overall": {role: round(score, 2) for role, score in totals.items()},
        "winner": winner,
        "summary": "Scores generated via fallback heuristic.",
        "review": {
            "pro": {
                "strengths": [
                    "Consistent participation across turns.",
                ],
                "improvements": [
                    "Incorporate more evidence to reinforce claims.",
                ],
            },
            "con": {
                "strengths": [
                    "Provided clear rebuttals despite heuristic scoring.",
                ],
                "improvements": [
                    "Expand on counterarguments to balance the discussion.",
                ],
            },
            "overall": "Heuristic review generated while Gemini was unavailable.",
        },
    }


def _normalise_scores(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure Gemini responses follow the expected schema."""

    normalised: Dict[str, Any] = dict(payload)
    per_argument: List[Dict[str, Any]] = []
    for entry in normalised.get("per_argument", []) or []:
        score = float(entry.get("score", 0)) if entry.get("score") is not None else 0.0
        turn_value = entry.get("turn")
        try:
            turn_index = int(turn_value)
        except (TypeError, ValueError):
            turn_index = turn_value
        rating = (
            entry.get("rating")
            or entry.get("rating_label")
            or entry.get("ratingLabel")
            or entry.get("score_label")
            or entry.get("assessment")
        )
        cleaned = {
            "turn": turn_index,
            "role": entry.get("role"),
            "score": round(score, 2),
            "rating": str(rating) if rating else _label_for_score(score),
            "feedback": entry.get("feedback") or entry.get("comment") or "",
        }
        per_argument.append(cleaned)
    normalised["per_argument"] = per_argument

    review = normalised.get("review") or {}
    participants: Dict[str, Dict[str, List[str]]] = {}
    for role_key in ("pro", "con"):
        role_review = review.get(role_key) or review.get(role_key.upper()) or {}
        strengths = _ensure_list(
            role_review.get("strengths")
            or role_review.get("positives")
            or role_review.get("good")
        )
        improvements = _ensure_list(
            role_review.get("improvements")
            or role_review.get("development")
            or role_review.get("weaknesses")
            or role_review.get("bad")
        )
        participants[role_key] = {
            "strengths": strengths,
            "improvements": improvements,
        }
    normalised["review"] = {
        "pro": participants.get("pro", {"strengths": [], "improvements": []}),
        "con": participants.get("con", {"strengths": [], "improvements": []}),
        "overall": review.get("overall")
        or review.get("summary")
        or normalised.get("summary", ""),
    }
    return normalised


def _label_for_score(score: float) -> str:
    if score >= 8.5:
        return "Outstanding"
    if score >= 7:
        return "Strong"
    if score >= 5.5:
        return "Competent"
    if score >= 4:
        return "Developing"
    return "Needs Improvement"


def _ensure_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


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
