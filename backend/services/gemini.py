"""Integration helpers for Google's Gemini multimodal API."""
from __future__ import annotations

import logging
import json
import random
from typing import Any, Dict, Iterable, List, Optional

from backend.config import settings
from backend.models.session import Argument

try:  # pragma: no cover - optional dependency during tests
    import google.generativeai as genai
except ImportError:  # pragma: no cover - fallback when package missing
    genai = None  # type: ignore[assignment]

_logger = logging.getLogger(__name__)
_CONFIGURED = False

FALLBACK_TOPICS: List[str] = [
    "This House believes that governments should strictly regulate artificial intelligence, even at the cost of slower innovation.",
    "Tech companies, not governments, should bear primary responsibility for harms caused by AI systems.",
    "The use of AI in warfare should be banned under international law.",
    "AI will ultimately create more jobs than it destroys.",
    "Social media algorithms should be transparent and open to public auditing.",
    "Tech companies should be held legally liable for the spread of deepfakes.",
    "Governments should have the power to shut down social media during times of unrest.",
    "The EU AI Act will become the global model for regulating artificial intelligence.",
    "Countries that cannot develop their own AI models will become digital colonies of AI superpowers.",
    "UNESCO's new standards on neurotechnology are an overreaction that will unnecessarily slow scientific progress.",
    "Rich countries should pay climate reparations to developing nations most affected by global warming.",
    "Developing countries should be allowed to prioritize economic growth over climate commitments.",
    "The world should phase out all fossil fuels by 2050, with no exceptions.",
    "Climate change is a bigger threat to global security than terrorism.",
    "AI will help more than it harms in the fight against climate change.",
    "Individual lifestyle changes (diet, travel, consumption) matter more than government policy in tackling climate change.",
    "The current international system (UN, IMF, World Bank) is failing and must be fundamentally redesigned.",
    "Rising tensions between the US and China over technology will define global politics in the next decade.",
    "Economic sanctions do more harm than good.",
    "The world should move toward a single global digital currency.",
    "Humanitarian intervention should be mandatory when governments commit mass human rights abuses.",
    "The age of nation-states is ending; global problems need global governance.",
    "A universal basic income is the best response to AI-driven job losses.",
    "Billionaires should not exist in a just society.",
    "Global trade agreements benefit corporations more than ordinary workers.",
    "Remote work should remain the default for knowledge workers after the pandemic era.",
    "The gig economy (Uber, Foodpanda, freelancing platforms) exploits workers more than it empowers them.",
    "Governments should heavily tax automated companies that replace human workers with AI and robots.",
    "Governments should have no role in regulating online speech beyond existing offline laws.",
    "Pakistan's recent social media regulations are necessary to combat fake news.",
    "Social media platforms should be treated as public utilities, not private companies.",
    "Anonymity on the internet does more harm than good.",
    "Internet shutdowns can never be justified in a democracy.",
    "Platforms should be legally required to remove hate speech and misinformation within 24 hours.",
    "Digital surveillance in the name of national security is a serious threat to human rights.",
    "Feminism is misunderstood and unfairly demonized in many conservative societies.",
    "Pakistan's progress on gender equality is more symbolic than real.",
    "Online harassment is the biggest barrier to women's participation in digital spaces.",
    "Quotas for women in parliament and corporate boards are necessary to speed up equality.",
    "Media in Pakistan does more to reinforce gender stereotypes than to challenge them.",
    "Schools should teach consent, gender equality, and digital safety as compulsory subjects.",
    "Social movements like Aurat March are essential for democracy.",
    "Traditional exams should be replaced with project-based assessment.",
    "Universities focus too much on theory and not enough on real-world skills.",
    "Studying abroad contributes to \"brain drain\" and harms developing countries.",
    "Schools should ban smartphones during class time.",
    "Governments should subsidize higher education for all, not just top performers.",
    "English-medium education is increasing inequality in countries like Pakistan.",
    "Pop culture (Netflix, K-dramas, TikTok) has more influence on youth values than family or religion.",
    "Mental health services should be free and integrated into all schools and universities.",
    "Pakistan's priority should be education reform rather than mega infrastructure projects.",
    "Pakistan needs stronger data protection and privacy laws, even if they make business harder.",
    "Internet shutdowns and platform bans are damaging Pakistan's democracy and economy.",
    "Pakistan should invest more in renewable energy than in traditional power projects.",
]


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
    return random.sample(FALLBACK_TOPICS, k=3)


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
            "You are an impartial debate adjudicator. Analyse every turn"
            " independently before reaching a conclusion. For each argument,"
            " score it from 1-10, assign a concise rating label (Outstanding,"
            " Strong, Competent, Developing, Needs Improvement), and offer"
            " direct feedback referencing the speaker's claims."
            "\nReturn a strict JSON object with these keys:\n"
            "- per_argument: list where every item contains turn, role, score,"
            " rating, feedback, strengths (list of positive notes) and"
            " improvements (list of actionable fixes)."
            "- overall: aggregate numeric score per role."
            "- winner: 'pro', 'con' or 'tie'."
            "- summary: 2-3 sentence justification for the decision."
            "- review: object with keys pro, con, and overall. pro/con must each"
            " include strengths (list), improvements (list), and summary"
            " (string describing how they performed). The overall key should"
            " summarise the debate plus include overall_highlights (list of good"
            " moments) and overall_growth (list of weaknesses)."
            f"\nDebate topic: {topic!r}."
        )
        if session_metadata:
            prompt += f" Additional context: {session_metadata}."
        try:
            model = genai.GenerativeModel(settings.gemini_model)
            response = model.generate_content(
                [
                    {"text": prompt},
                    {"text": "Transcript:"},
                    {"text": json.dumps(arguments_payload)},
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
                "strengths": [
                    "Shared a coherent point despite offline scoring.",
                ],
                "improvements": [
                    "Add evidence or examples to make the claim more persuasive.",
                ],
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
                "summary": "Stayed active despite heuristic judging.",
            },
            "con": {
                "strengths": [
                    "Provided clear rebuttals despite heuristic scoring.",
                ],
                "improvements": [
                    "Expand on counterarguments to balance the discussion.",
                ],
                "summary": "Kept the exchange balanced with timely rebuttals.",
            },
            "overall": "Heuristic review generated while Gemini was unavailable.",
            "overall_highlights": [
                "Both speakers maintained civil discourse despite offline scoring.",
            ],
            "overall_growth": [
                "Future debates should cite more specific evidence.",
            ],
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
            "strengths": _ensure_list(entry.get("strengths") or entry.get("positives")),
            "improvements": _ensure_list(
                entry.get("improvements")
                or entry.get("development")
                or entry.get("weaknesses")
            ),
        }
        per_argument.append(cleaned)
    normalised["per_argument"] = per_argument

    review = normalised.get("review") or {}
    participants: Dict[str, Dict[str, List[str]]] = {}
    for role_key in ("pro", "con"):
        role_review = review.get(role_key) or review.get(role_key.upper()) or {}
        participants[role_key] = _normalise_review_section(role_review)
    normalised["review"] = {
        "pro": participants.get("pro", {"strengths": [], "improvements": [], "summary": ""}),
        "con": participants.get("con", {"strengths": [], "improvements": [], "summary": ""}),
        "overall": review.get("overall")
        or review.get("summary")
        or normalised.get("summary", ""),
        "overallHighlights": _ensure_list(
            review.get("overall_highlights")
            or review.get("highlights")
            or review.get("positives")
            or review.get("good")
        ),
        "overallImprovements": _ensure_list(
            review.get("overall_growth")
            or review.get("growth")
            or review.get("opportunities")
            or review.get("negatives")
            or review.get("bad")
        ),
    }
    return normalised


def _normalise_review_section(section: Dict[str, Any]) -> Dict[str, Any]:
    strengths = _ensure_list(
        section.get("strengths") or section.get("positives") or section.get("good")
    )
    improvements = _ensure_list(
        section.get("improvements")
        or section.get("development")
        or section.get("weaknesses")
        or section.get("bad")
    )
    summary = section.get("summary") or section.get("overall") or ""
    return {
        "strengths": strengths,
        "improvements": improvements,
        "summary": summary,
    }


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
