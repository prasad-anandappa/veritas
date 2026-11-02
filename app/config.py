"""Configuration for Veritas.

Everything is driven by environment variables so the same code runs in
deterministic MOCK mode (no credentials — used for the demo and the tests)
and in LIVE mode (real Tavily search + real Nebius Token Factory inference)
when keys are dropped in. No code changes are needed to switch.

Live mode is per-component:
  * Search is LIVE when ``TAVILY_API_KEY`` is set, MOCK otherwise.
  * LLM is LIVE when ``NEBIUS_API_KEY`` (or ``TOKEN_FACTORY_API_KEY``) is
    set, MOCK otherwise.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
DEFAULT_NEBIUS_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
TAVILY_BASE_URL = "https://api.tavily.com"


@dataclass(frozen=True)
class Settings:
    tavily_api_key: str = ""
    nebius_api_key: str = ""
    nebius_base_url: str = DEFAULT_NEBIUS_BASE_URL
    nebius_model: str = DEFAULT_NEBIUS_MODEL
    max_sub_questions: int = 4
    results_per_query: int = 5
    max_sources: int = 12

    @property
    def search_live(self) -> bool:
        return bool(self.tavily_api_key)

    @property
    def llm_live(self) -> bool:
        return bool(self.nebius_api_key)

    @property
    def mode(self) -> str:
        """'live' only when both mandatory services are live."""
        if self.search_live and self.llm_live:
            return "live"
        if not self.search_live and not self.llm_live:
            return "mock"
        return "partial"

    def mode_detail(self) -> dict:
        return {
            "mode": self.mode,
            "search": "tavily-live" if self.search_live else "mock-fixtures",
            "llm": (
                f"nebius-token-factory:{self.nebius_model}"
                if self.llm_live
                else "mock-deterministic"
            ),
        }


def load_settings() -> Settings:
    nebius_key = (
        os.environ.get("NEBIUS_API_KEY", "").strip()
        or os.environ.get("TOKEN_FACTORY_API_KEY", "").strip()
    )
    nebius_base = (
        os.environ.get("NEBIUS_BASE_URL", "").strip()
        or os.environ.get("TOKEN_FACTORY_BASE_URL", "").strip()
        or DEFAULT_NEBIUS_BASE_URL
    )
    nebius_model = (
        os.environ.get("NEBIUS_MODEL", "").strip()
        or os.environ.get("TOKEN_FACTORY_MODEL", "").strip()
        or DEFAULT_NEBIUS_MODEL
    )
    return Settings(
        tavily_api_key=os.environ.get("TAVILY_API_KEY", "").strip(),
        nebius_api_key=nebius_key,
        nebius_base_url=nebius_base.rstrip("/"),
        nebius_model=nebius_model,
    )
