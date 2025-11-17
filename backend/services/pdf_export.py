"""Generate a PDF transcript summarising the debate results."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Iterable

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from backend.models.session import Argument, DebateSession, SessionResult


def render_pdf(session: DebateSession, result: SessionResult) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    def _write_line(text: str, y_pos: float, font_size: int = 12) -> float:
        pdf.setFont("Helvetica", font_size)
        pdf.drawString(1 * inch, y_pos, text[:120])
        return y_pos - 14

    y = height - 1 * inch
    pdf.setTitle(f"Debate Results - {session.chosen_topic or session.session_id}")
    y = _write_line("Letsee Debate Transcript", y, 16)
    y = _write_line(f"Session: {session.session_id}", y)
    y = _write_line(f"Topic: {session.chosen_topic or 'Pending'}", y)
    y = _write_line(f"Generated: {datetime.utcnow():%Y-%m-%d %H:%M UTC}", y)

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(1 * inch, y, "Participants")
    y -= 18
    pdf.setFont("Helvetica", 11)
    for role, participant in session.participants.items():
        y = _write_line(f"{role.value.upper()}: {participant.name}", y)

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(1 * inch, y, "Transcript")
    y -= 18
    pdf.setFont("Helvetica", 10)
    for argument in session.transcript:
        block = f"Turn {argument.turn_index + 1} ({argument.speaker_role.value} - {argument.speaker_name}):"
        y = _write_line(block, y)
        lines = _wrap_text(argument.content, 90)
        for line in lines:
            if y < 1 * inch:
                pdf.showPage()
                y = height - 1 * inch
                pdf.setFont("Helvetica", 10)
            y = _write_line(line, y)
        y -= 6

    if y < 2 * inch:
        pdf.showPage()
        y = height - 1 * inch

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(1 * inch, y, "Results")
    y -= 18
    pdf.setFont("Helvetica", 11)
    winner_text = result.winner_role.value if result.winner_role else "Tie"
    y = _write_line(f"Winner: {winner_text}", y)
    y = _write_line(f"Summary: {result.rationale}", y)
    y -= 6
    pdf.setFont("Helvetica", 10)
    for entry in result.per_argument_scores:
        line = (
            f"Turn {entry.get('turn')} - {entry.get('role')}"
            f" | Score: {entry.get('score')} | {entry.get('feedback')}"
        )
        if y < 1 * inch:
            pdf.showPage()
            y = height - 1 * inch
            pdf.setFont("Helvetica", 10)
        y = _write_line(line, y)

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
