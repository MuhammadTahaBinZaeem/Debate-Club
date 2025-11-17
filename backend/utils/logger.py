"""Structured logging helpers."""
from __future__ import annotations

import logging
from typing import Any, Dict


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def log_event(logger: logging.Logger, event: str, **payload: Dict[str, Any]) -> None:
    logger.info("%s | payload=%s", event, payload)
