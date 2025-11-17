"""Integration helpers for Google's Gemini multimodal API."""
from __future__ import annotations

import logging
import json
import random
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

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
    return _heuristic_debate_scores(arguments_payload, topic)


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


EVIDENCE_KEYWORDS: Tuple[str, ...] = (
    "according to",
    "study",
    "report",
    "data",
    "survey",
    "research",
    "evidence",
    "analysis",
    "statistic",
    "%",
)

CONNECTOR_KEYWORDS: Tuple[str, ...] = (
    "because",
    "therefore",
    "however",
    "moreover",
    "furthermore",
    "meanwhile",
    "consequently",
    "additionally",
    "firstly",
    "secondly",
    "finally",
    "nevertheless",
)

FALLACY_KEYWORDS: Tuple[str, ...] = (
    "ad hominem",
    "strawman",
    "slippery slope",
    "red herring",
    "false dichotomy",
    "appeal to emotion",
    "bandwagon",
)

TOPIC_RULES: Dict[str, Dict[str, Sequence[str]]] = {
    "ai": {
        "match": ("ai", "artificial intelligence", "automation", "machine learning"),
        "keywords": ("algorithm", "data", "model", "bias", "ethics", "automation"),
    },
    "climate": {
        "match": ("climate", "emission", "carbon", "warming", "environment"),
        "keywords": ("carbon", "emissions", "renewable", "solar", "climate", "resilience"),
    },
    "governance": {
        "match": ("government", "policy", "regulation", "law", "state"),
        "keywords": ("policy", "regulation", "compliance", "oversight", "legislation"),
    },
    "education": {
        "match": ("school", "education", "university", "students"),
        "keywords": ("curriculum", "learning", "teacher", "students", "assessment"),
    },
    "economy": {
        "match": ("economy", "economic", "jobs", "trade", "market"),
        "keywords": ("investment", "growth", "employment", "inflation", "market"),
    },
}


def _heuristic_debate_scores(
    arguments: Sequence[Dict[str, Any]],
    topic: str,
) -> Dict[str, Any]:
    topic_profiles = _identify_topic_profiles(topic)
    per_argument: List[Dict[str, Any]] = []
    totals: Dict[str, float] = {}
    role_strengths: Dict[str, List[str]] = {}
    role_improvements: Dict[str, List[str]] = {}

    for argument in arguments:
        evaluation = _score_argument(argument, topic_profiles)
        per_argument.append(evaluation["result"])
        role = argument["role"]
        totals[role] = totals.get(role, 0.0) + evaluation["result"]["score"]
        role_strengths.setdefault(role, [])
        role_improvements.setdefault(role, [])
        role_strengths[role].extend(evaluation["strength_notes"])
        role_improvements[role].extend(evaluation["improvement_notes"])

    overall = {role: round(score, 2) for role, score in totals.items()}
    if not overall:
        winner = "tie"
    else:
        ordered = sorted(overall.items(), key=lambda item: item[1], reverse=True)
        if len(ordered) > 1 and abs(ordered[0][1] - ordered[1][1]) < 0.5:
            winner = "tie"
        else:
            winner = ordered[0][0]

    summary = _build_overall_summary(topic, overall, winner)
    review = _build_review_section(role_strengths, role_improvements, per_argument, summary)

    return {
        "per_argument": per_argument,
        "overall": overall,
        "winner": winner,
        "summary": summary,
        "review": review,
    }


def _score_argument(
    argument: Dict[str, Any],
    topic_profiles: Sequence[str],
) -> Dict[str, Any]:
    content = argument.get("content", "")
    role = argument.get("role", "")
    turn = argument.get("turn")
    time_taken = argument.get("time_taken") or 0.0
    text_lower = content.lower()

    score = 5.0
    strengths: List[str] = []
    improvements: List[str] = []
    feature_notes: List[str] = []

    word_count = _count_words(content)
    length_bonus = min(word_count / 50.0, 3.0)
    score += length_bonus
    if length_bonus >= 1.0:
        strengths.append("Developed the point with substantive detail.")
    elif word_count < 40:
        improvements.append("Spend more time elaborating on the claim.")
    feature_notes.append(f"Length bonus: +{length_bonus:.2f}")

    evidence_hits = _count_keyword_hits(text_lower, EVIDENCE_KEYWORDS) + _count_numeric_tokens(content)
    evidence_bonus = min(evidence_hits * 0.5, 2.0)
    score += evidence_bonus
    if evidence_bonus:
        strengths.append("Referenced evidence or data.")
    else:
        improvements.append("Cite data or examples to anchor the reasoning.")
    feature_notes.append(f"Evidence bonus: +{evidence_bonus:.2f}")

    connector_hits = _count_keyword_hits(text_lower, CONNECTOR_KEYWORDS)
    connector_bonus = min(connector_hits * 0.3, 1.0)
    score += connector_bonus
    if connector_bonus:
        strengths.append("Used logical connectors to structure the flow.")
    else:
        improvements.append("Signal transitions with connectors to improve clarity.")
    feature_notes.append(f"Connector bonus: +{connector_bonus:.2f}")

    clarity_bonus = _sentence_clarity_bonus(content)
    score += clarity_bonus
    if clarity_bonus >= 0.5:
        strengths.append("Sentences were clear and well-paced.")
    else:
        improvements.append("Balance sentence lengths for smoother delivery.")
    feature_notes.append(f"Clarity bonus: +{clarity_bonus:.2f}")

    fallacy_hits = _count_keyword_hits(text_lower, FALLACY_KEYWORDS)
    fallacy_penalty = fallacy_hits * 1.0
    score -= fallacy_penalty
    if fallacy_hits:
        improvements.append("Avoid common logical fallacies in rebuttals.")
    feature_notes.append(f"Fallacy penalty: -{fallacy_penalty:.2f}")

    time_penalty = _time_efficiency_penalty(time_taken)
    score -= time_penalty
    if time_penalty > 0.25:
        improvements.append("Align pacing closer to the allotted time.")
    feature_notes.append(f"Time penalty: -{time_penalty:.2f}")

    topic_bonus = _topic_specific_bonus(text_lower, topic_profiles)
    score += topic_bonus
    if topic_bonus:
        strengths.append("Connected arguments to the specific debate theme.")
    else:
        improvements.append("Tie arguments explicitly to the topic's core issues.")
    feature_notes.append(f"Topic relevance bonus: +{topic_bonus:.2f}")

    final_score = max(1.0, min(10.0, round(score, 2)))
    rating = _label_for_score(final_score)

    feedback = "; ".join(feature_notes)
    result = {
        "turn": turn,
        "role": role,
        "score": final_score,
        "rating": rating,
        "strengths": _deduplicate(strengths),
        "improvements": _deduplicate(improvements),
        "feedback": feedback,
    }

    return {
        "result": result,
        "strength_notes": _deduplicate(strengths),
        "improvement_notes": _deduplicate(improvements),
    }


def _identify_topic_profiles(topic: str) -> List[str]:
    topic_lower = topic.lower()
    profiles: List[str] = []
    for name, rule in TOPIC_RULES.items():
        if any(keyword in topic_lower for keyword in rule["match"]):
            profiles.append(name)
    return profiles


def _topic_specific_bonus(text_lower: str, topic_profiles: Sequence[str]) -> float:
    bonus = 0.0
    for profile in topic_profiles:
        keywords = TOPIC_RULES[profile]["keywords"]
        matches = _count_keyword_hits(text_lower, keywords)
        bonus += min(matches * 0.2, 0.6)
    return min(bonus, 1.0)


def _count_words(text: str) -> int:
    tokens = [token for token in re.split(r"\s+", text.strip()) if token]
    return len(tokens)


def _count_numeric_tokens(text: str) -> int:
    return len(re.findall(r"\b\d+\b", text))


def _count_keyword_hits(text_lower: str, keywords: Sequence[str]) -> int:
    hits = 0
    for keyword in keywords:
        if keyword and keyword in text_lower:
            hits += text_lower.count(keyword)
    return hits


def _sentence_clarity_bonus(text: str) -> float:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"[.!?]", text)
        if sentence.strip()
    ]
    if not sentences:
        return 0.0
    words_per_sentence = [max(1, _count_words(sentence)) for sentence in sentences]
    average = sum(words_per_sentence) / len(words_per_sentence)
    deviation = abs(average - 20)
    clarity = max(0.0, 1.0 - (deviation / 20.0))
    return round(clarity, 2)


def _time_efficiency_penalty(time_taken: float) -> float:
    if not time_taken:
        return 0.25  # light penalty when timing is unavailable
    deviation = abs(time_taken - 30.0)
    penalty = min(deviation / 60.0, 0.5)
    return round(penalty, 2)


def _build_overall_summary(topic: str, totals: Dict[str, float], winner: str) -> str:
    if not totals:
        return "No arguments were provided, resulting in a neutral outcome."
    if winner == "tie":
        return (
            f"Both sides were evenly matched on '{topic}', with balanced scores "
            "after applying the heuristic rubric."
        )
    losing_role = next((role for role in totals.keys() if role != winner), None)
    margin = 0.0
    if losing_role:
        margin = round(totals[winner] - totals.get(losing_role, 0.0), 2)
    return (
        f"{winner.capitalize()} held the edge on '{topic}' by {margin:.2f} points "
        "through stronger structure and evidence despite heuristic judging."
    )


def _build_review_section(
    role_strengths: Dict[str, List[str]],
    role_improvements: Dict[str, List[str]],
    per_argument: Sequence[Dict[str, Any]],
    summary: str,
) -> Dict[str, Any]:
    def summarise_role(role: str) -> Dict[str, Any]:
        strengths = _deduplicate(role_strengths.get(role, []))[:4]
        improvements = _deduplicate(role_improvements.get(role, []))[:4]
        summary_text = (
            f"{role.capitalize()} leveraged {', '.join(strengths[:2])}" if strengths else ""
        )
        if improvements and not summary_text:
            summary_text = f"{role.capitalize()} can improve by {', '.join(improvements[:2])}"
        if not summary_text:
            summary_text = f"{role.capitalize()} can improve with more structured analysis."
        return {
            "strengths": strengths,
            "improvements": improvements,
            "summary": summary_text,
        }

    highlights = [
        f"Turn {item['turn']} ({item['role']}): {item['rating']}"
        for item in per_argument
        if item.get("rating") in ("Outstanding", "Strong")
    ][:3]
    improvements_list = [
        f"Turn {item['turn']} ({item['role']}): needs clearer evidence"
        for item in per_argument
        if item.get("rating") in ("Developing", "Needs Improvement")
    ][:3]

    return {
        "pro": summarise_role("pro"),
        "con": summarise_role("con"),
        "overall": {
            "notes": summary,
            "overall_highlights": highlights,
            "overall_improvements": improvements_list,
        },
    }


def _deduplicate(items: Sequence[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


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
