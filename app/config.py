"""Configuration for Veritas.

Everything is driven by environment variables so the same code runs in
deterministic MOCK mode (no credentials — used for the demo and the tests)
and in LIVE mode (real Tavily search + real Nebius Token Factory inference)
when keys are dropped in. No code changes are needed to switch.

Live mode is per-component:
  * Search is LIVE when ``TAVILY_API_KEY`` is set, MOCK otherwise.
  * LLM is LIVE when an LLM backend key is set, MOCK otherwise. Two live
    backends speak the same OpenAI-compatible wire format:
      - **Otari gateway** (Mozilla AI, hosted at otari.ai) when
        ``OTARI_API_KEY`` (or ``OTARI_AI_TOKEN``) is set — takes
        precedence when both are configured;
      - **Nebius Token Factory** when ``NEBIUS_API_KEY`` (or
        ``TOKEN_FACTORY_API_KEY``) is set.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
DEFAULT_NEBIUS_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
# Hosted Otari gateway (Mozilla AI): OpenAI-compatible base URL; the model
# is a "provider:model" string the gateway routes on (take the available
# ids from otari.ai). Default routes Llama 3.3 70B (open-weight) via Groq.
DEFAULT_OTARI_BASE_URL = "https://api.otari.ai/v1"
DEFAULT_OTARI_MODEL = "groq:llama-3.3-70b-versatile"
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
    otari_api_key: str = ""
    otari_base_url: str = DEFAULT_OTARI_BASE_URL
    otari_model: str = DEFAULT_OTARI_MODEL

    @property
    def search_live(self) -> bool:
        return bool(self.tavily_api_key)

    @property
    def llm_live(self) -> bool:
        return bool(self.nebius_api_key or self.otari_api_key)

    @property
    def llm_backend(self) -> str:
        """Which LLM backend the factory will build: otari > nebius > mock."""
        if self.otari_api_key:
            return "otari"
        if self.nebius_api_key:
            return "nebius"
        return "mock"

    @property
    def mode(self) -> str:
        """'live' only when both mandatory services are live."""
        if self.search_live and self.llm_live:
            return "live"
        if not self.search_live and not self.llm_live:
            return "mock"
        return "partial"

    def mode_detail(self) -> dict:
        llm = {
            "otari": f"otari:{self.otari_model}",
            "nebius": f"nebius-token-factory:{self.nebius_model}",
            "mock": "mock-deterministic",
        }[self.llm_backend]
        return {
            "mode": self.mode,
            "search": "tavily-live" if self.search_live else "mock-fixtures",
            "llm": llm,
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
    otari_key = (
        os.environ.get("OTARI_API_KEY", "").strip()
        or os.environ.get("OTARI_AI_TOKEN", "").strip()
    )
    otari_base = (
        os.environ.get("OTARI_BASE_URL", "").strip() or DEFAULT_OTARI_BASE_URL
    )
    otari_model = (
        os.environ.get("OTARI_MODEL", "").strip() or DEFAULT_OTARI_MODEL
    )
    return Settings(
        tavily_api_key=os.environ.get("TAVILY_API_KEY", "").strip(),
        nebius_api_key=nebius_key,
        nebius_base_url=nebius_base.rstrip("/"),
        nebius_model=nebius_model,
        otari_api_key=otari_key,
        otari_base_url=otari_base.rstrip("/"),
        otari_model=otari_model,
    )
