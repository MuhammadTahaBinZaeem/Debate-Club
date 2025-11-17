"""Utilities for moderating debate messages."""
from __future__ import annotations

import re
from typing import List, Tuple


# Basic placeholder phrases. In production this could be loaded from a DB or service.
PROHIBITED_PHRASES: List[str] = [
    "hate",
    "violence",
    "terror",
]


def censor_message(message: str) -> Tuple[str, List[str]]:
    """Return a censored version of the message and any violations detected."""

    violations: List[str] = []
    sanitized = message
    for phrase in PROHIBITED_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        if pattern.search(sanitized):
            violations.append(phrase)
            sanitized = pattern.sub(lambda match: "*" * len(match.group(0)), sanitized)
    return sanitized, violations
