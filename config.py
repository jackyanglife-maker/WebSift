"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the WebSift application."""

    anthropic_api_key: str
    database_url: str
    max_content_length: int
    request_timeout: int
    playwright_fallback_threshold: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./websift.db"),
        max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", "8000")),
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
        playwright_fallback_threshold=int(
            os.getenv("PLAYWRIGHT_FALLBACK_THRESHOLD", "500")
        ),
    )
