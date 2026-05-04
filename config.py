"""Environment and runtime configuration (no secrets in code)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    default_model: str
    history_path: str


def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        default_model=os.getenv("OPENAI_AGENT_MODEL", "gpt-4o-mini"),
        history_path=os.getenv("HISTORY_JSON_PATH", "history.json"),
    )


def require_api_key() -> str:
    key = get_settings().openai_api_key
    if not key or key.strip() == "" or "your_openai" in key.lower():
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Copy .env.example to .env and set a valid key."
        )
    return key
