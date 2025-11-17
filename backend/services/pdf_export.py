"""Generate a PDF transcript summarising the debate results."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from backend.models.session import Argument, DebateSession, ParticipantRole, SessionResult


def render_pdf(session: DebateSession, result: SessionResult) -> bytes:
    """Render a multi-section PDF that mirrors the in-app judging layout."""

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    pdf.setTitle(f"Debate Results - {session.chosen_topic or session.session_id}")

    # Layout helpers -----------------------------------------------------
    def _draw_backdrop() -> None:
        pdf.saveState()
        sidebar_width = 0.85 * inch
        pdf.setFillColor(colors.HexColor("#111318"))
        pdf.rect(0, 0, sidebar_width, height, fill=1, stroke=0)
        pdf.setStrokeColor(colors.HexColor("#f2f2f2"))
        pdf.setLineWidth(0.2)
        step = 32
        start_x = -int(height)
        while start_x < int(width):
            pdf.line(sidebar_width + start_x, 0, sidebar_width + start_x + height, height)
            start_x += step
        pdf.restoreState()

    def _draw_page_header(title: str, subtitle: str) -> None:
        pdf.saveState()
        pdf.setFillColor(colors.HexColor("#1b1f2b"))
        pdf.rect(0.85 * inch, height - 0.9 * inch, width - 0.85 * inch, 0.9 * inch, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(1 * inch, height - 0.45 * inch, title[:80])
        pdf.setFont("Helvetica", 10)
        pdf.drawString(1 * inch, height - 0.85 * inch + 12, subtitle[:120])
        timestamp = datetime.utcnow().strftime("Generated %Y-%m-%d %H:%M UTC")
        pdf.drawRightString(width - 0.5 * inch, height - 0.45 * inch, timestamp)
        pdf.restoreState()

    def _draw_footer(page_num: int) -> None:
        pdf.saveState()
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(colors.HexColor("#4e566a"))
        pdf.drawCentredString((width + 0.85 * inch) / 2, 0.55 * inch, f"Page {page_num}")
        pdf.restoreState()

    y = height - 1.35 * inch
    page_number = 1

    def _prepare_page(title: str, subtitle: str, fresh_page: bool) -> None:
        nonlocal y, page_number
        if fresh_page:
            _draw_footer(page_number)
            pdf.showPage()
            page_number += 1
        _draw_backdrop()
        _draw_page_header(title, subtitle)
        y = height - 1.35 * inch

    def _write_heading(text: str, y_pos: float) -> float:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColor(colors.HexColor("#1a1a1a"))
        pdf.drawString(1 * inch, y_pos, text)
        return y_pos - 18

    def _write_body(text: str, y_pos: float, font_size: int = 10, indent: float = 0.0) -> float:
        pdf.setFont("Helvetica", font_size)
        pdf.setFillColor(colors.HexColor("#222222"))
        indent_offset = 1 * inch + indent
        for line in _wrap_text(text, 100):
            pdf.drawString(indent_offset, y_pos, line)
            y_pos -= font_size + 2
        return y_pos

    def _write_bullet(text: str, y_pos: float) -> float:
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.HexColor("#222222"))
        pdf.drawString(1 * inch, y_pos, "•")
        return _write_body(text, y_pos, font_size=10, indent=12)

    def _ensure_space(min_height: float, title: str, subtitle: str) -> None:
        if y < min_height:
            _prepare_page(title, subtitle, fresh_page=True)

    # Cover page ---------------------------------------------------------
    topic_text = session.chosen_topic or "Awaiting topic"
    subtitle = f"Session {session.session_id} · Invite code {session.invite_code}"
    _prepare_page(f"{{{topic_text}}}", subtitle, fresh_page=False)

    pdf.setFont("Helvetica-Bold", 26)
    pdf.setFillColor(colors.HexColor("#111318"))
    pdf.drawString(1 * inch, y, "Debate Club Report")
    y -= 34
    pdf.setFont("Helvetica", 12)
    opening = (
        "Official transcript and scoring report covering every turn, judge "
        "rationale, and actionable recommendations."
    )
    y = _write_body(opening, y - 10, font_size=12)

    y = _write_heading("Session snapshot", y - 10)
    session_created = session.created_at.strftime("%B %d, %Y %H:%M UTC")
    mode_value = str(session.metadata.get("mode", "invite")).title()
    refreshes = session.metadata.get("topicRefreshes", session.topic_refreshes)
    stats = [
        f"Mode: {mode_value} | Topic refreshes: {refreshes}",
        f"Created: {session_created}",
        f"Max turns: {session.max_turns} · Per-turn limit: {session.per_turn_limit}s",
        f"Total elapsed: {session.total_elapsed_seconds or 0}s",
    ]
    for stat in stats:
        y = _write_body(stat, y)

    # Summary + agenda page ---------------------------------------------
    _prepare_page("Briefing", "Participants, agenda, and overview", fresh_page=True)

    y = _write_heading("Participants", y)
    for role in ParticipantRole:
        participant = session.participants.get(role)
        display_name = participant.name if participant else "—"
        y = _write_body(f"{role.name.title()}: {display_name}", y)
        if participant:
            detail = f"Time active: {participant.time_spent_seconds}s | Warnings: {participant.warnings}"
            y = _write_body(detail, y, font_size=9, indent=12)

    agenda_title = "Agenda"
    y = _write_heading(agenda_title, y - 4)
    if session.transcript:
        for argument in session.transcript[:6]:
            label = (
                f"Turn {argument.turn_index + 1}: {argument.speaker_role.name.title()} "
                f"({argument.speaker_name})"
            )
            y = _write_bullet(label, y)
    else:
        y = _write_body("Debate scheduled – turns have not started yet.", y)

    overview_title = "Overview"
    y = _write_heading(overview_title, y - 4)
    rationale = result.rationale or "The judge has not published a rationale yet."
    y = _write_body(rationale, y)
    summary_points = [
        f"Winner: {result.winner_role.value if result.winner_role else 'Tie'}",
        f"Turns recorded: {len(session.transcript)}",
        f"Flagged for review: {'Yes' if result.flagged_for_review else 'No'}",
    ]
    for item in summary_points:
        y = _write_body(item, y, font_size=10)

    # Transcript ---------------------------------------------------------
    transcript_subtitle = "Verbatim speaker record"
    _prepare_page("Transcript", transcript_subtitle, fresh_page=True)
    if not session.transcript:
        y = _write_body("No turns were recorded for this session.", y)
    for argument in session.transcript:
        _ensure_space(1.5 * inch, "Transcript", f"{transcript_subtitle} (cont.)")
        block_header = (
            f"Turn {argument.turn_index + 1} – {argument.speaker_role.name.title()} "
            f"({argument.speaker_name})"
        )
        y = _write_body(block_header, y, font_size=11)
        y = _write_body(argument.content, y, font_size=10, indent=12)
        if argument.time_taken_seconds:
            y = _write_body(f"Time used: {argument.time_taken_seconds}s", y, font_size=9, indent=12)
        y -= 6

    # Results ------------------------------------------------------------
    results_subtitle = "Scores, notes, and improvement plan"
    _prepare_page("Judging", results_subtitle, fresh_page=True)

    y = _write_heading("Outcome", y)
    winner_text = result.winner_role.name.title() if result.winner_role else "Tie"
    y = _write_body(f"Winner: {winner_text}", y)

    if result.overall_score:
        y = _write_heading("Overall scores", y - 2)
        for role in ParticipantRole:
            score_val = result.overall_score.get(role)
            if score_val is None:
                score_val = result.overall_score.get(role.value)
            if score_val is None:
                continue
            participant = session.participants.get(role)
            name = participant.name if participant else role.name.title()
            y = _write_body(f"{name} – {score_val:.2f}/10", y, font_size=11)

    if result.per_argument_scores:
        y = _write_heading("Per-turn assessment", y - 2)
        for entry in result.per_argument_scores:
            _ensure_space(1.4 * inch, "Judging", f"{results_subtitle} (cont.)")
            turn_raw = entry.get("turn")
            try:
                turn_display = int(turn_raw) + 1
            except (TypeError, ValueError):
                turn_display = turn_raw
            role_label = entry.get("role", "")
            rating = entry.get("rating")
            score_text = entry.get("score")
            header = f"Turn {turn_display} · {role_label}"
            if score_text is not None:
                header += f" · Score {score_text}"
            if rating:
                header += f" ({rating})"
            y = _write_body(header, y, font_size=10)
            feedback = entry.get("feedback")
            if feedback:
                y = _write_body(str(feedback), y, font_size=9, indent=12)
            y -= 4

    review = result.review or {}
    if review:
        y = _write_heading("Judge review", y - 2)
        for role_key, label, participant_role in (
            ("pro", "Proponent", ParticipantRole.PROPONENT),
            ("con", "Opponent", ParticipantRole.OPPONENT),
        ):
            role_review = review.get(role_key)
            if not role_review:
                continue
            participant = session.participants.get(participant_role)
            name = participant.name if participant else label
            y = _write_body(f"{label} – {name}", y, font_size=11)
            strengths = role_review.get("strengths", [])
            improvements = role_review.get("improvements", [])
            summary = role_review.get("summary")
            if strengths:
                y = _write_body("Strengths:", y, font_size=10, indent=12)
                for item in strengths:
                    y = _write_bullet(str(item), y)
            if improvements:
                y = _write_body("Improvements:", y, font_size=10, indent=12)
                for item in improvements:
                    y = _write_bullet(str(item), y)
            if summary:
                y = _write_body(f"Summary: {summary}", y, font_size=10, indent=12)
            y -= 4

        overall_review = review.get("overall")
        if overall_review:
            y = _write_body("Overall assessment:", y, font_size=11)
            y = _write_body(str(overall_review), y, font_size=10, indent=12)

        highlights = review.get("overallHighlights") or review.get("overall_highlights") or []
        growth = review.get("overallImprovements") or review.get("overall_growth") or []
        if highlights:
            y = _write_heading("Highlights", y - 2)
            for item in highlights:
                y = _write_bullet(str(item), y)
        if growth:
            y = _write_heading("Growth priorities", y - 2)
            for item in growth:
                y = _write_bullet(str(item), y)

    _draw_footer(page_number)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()


def _wrap_text(text: str, width: int) -> Iterable[str]:
    words = text.split()
    line: list[str] = []
    current_len = 0
    for word in words:
        if current_len + len(word) + 1 > width:
            yield " ".join(line)
            line = [word]
            current_len = len(word)
        else:
            line.append(word)
            current_len += len(word) + 1
    if line:
        yield " ".join(line)
