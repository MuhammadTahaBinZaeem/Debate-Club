"""Application configuration for the debate platform backend."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Settings:
    """Simple settings container populated from environment variables."""

    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.0-pro")
    )
    qdrant_url: str = field(default_factory=lambda: os.getenv("QDRANT_URL", ""))
    qdrant_api_key: str = field(default_factory=lambda: os.getenv("QDRANT_API_KEY", ""))
    opus_api_key: str = field(default_factory=lambda: os.getenv("OPUS_API_KEY", ""))
    opus_workflow_id: str = field(default_factory=lambda: os.getenv("OPUS_WORKFLOW_ID", ""))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "letsee-secret"))

    default_turn_seconds: int = field(
        default_factory=lambda: int(os.getenv("TURN_SECONDS", "30"))
    )
    default_total_seconds: int = field(
        default_factory=lambda: int(os.getenv("TOTAL_SECONDS", "600"))
    )
    max_turns: int = field(default_factory=lambda: int(os.getenv("MAX_TURNS", "60")))
    topic_refresh_limit: int = field(
        default_factory=lambda: int(os.getenv("TOPIC_REFRESH_LIMIT", "1"))
    )

    cors_origins: List[str] = field(
        default_factory=lambda: [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
    )
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    app_host: str = field(default_factory=lambda: os.getenv("APP_HOST", "0.0.0.0"))
    app_port: int = field(default_factory=lambda: int(os.getenv("APP_PORT", "8000")))


settings = Settings()
