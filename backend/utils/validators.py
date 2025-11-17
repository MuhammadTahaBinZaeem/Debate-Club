"""Validation helpers for API inputs."""
from __future__ import annotations

from typing import Iterable, List


class ValidationError(ValueError):
    """Raised when client input fails validation."""


MAX_ARGUMENT_LENGTH = 2_000


def validate_topic_choice(topic: str, topics: Iterable[str]) -> str:
    if topic not in topics:
        raise ValidationError("Invalid topic selection")
    return topic


def validate_argument_length(message: str) -> str:
    if not message.strip():
        raise ValidationError("Argument cannot be empty")
    if len(message) > MAX_ARGUMENT_LENGTH:
        raise ValidationError("Argument too long")
    return message


def ensure_roles_present(roles: List[str]) -> None:
    if len(roles) < 2:
        raise ValidationError("Both participants must join before starting the debate")
