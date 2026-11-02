"""Search clients behind one interface.

``TavilySearchClient`` is the real thing (Tavily REST: /search + /extract).
``MockSearchClient`` serves the bundled fixture corpus deterministically.
The agent pipeline cannot tell them apart — same methods, same shapes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx

from .config import TAVILY_BASE_URL
from .fixtures import CORPUS
from .textutil import content_words


class SearchError(RuntimeError):
    pass


@dataclass
class RawHit:
    title: str
    url: str
    snippet: str = ""
    relevance: float = 0.0  # 0..1
    published_date: str | None = None


class SearchClient(Protocol):
    name: str

    def search(self, query: str, max_results: int = 5) -> list[RawHit]: ...

    def extract(self, urls: list[str]) -> dict[str, str]: ...


# ---------------------------------------------------------------------------
# Real Tavily client
# ---------------------------------------------------------------------------
class TavilySearchClient:
    """Real-time web search + full-text extraction via the Tavily API."""

    name = "tavily-live"

    def __init__(
        self,
        api_key: str,
        base_url: str = TAVILY_BASE_URL,
        http: httpx.Client | None = None,
    ):
        if not api_key:
            raise SearchError("TAVILY_API_KEY is required for the live client")
        self._key = api_key
        self._base = base_url.rstrip("/")
        self._http = http or httpx.Client(timeout=30.0, trust_env=False)

    def search(self, query: str, max_results: int = 5) -> list[RawHit]:
        try:
            resp = self._http.post(
                f"{self._base}/search",
                json={
                    "api_key": self._key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": max_results,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # network / HTTP / JSON — surface, don't hide
            raise SearchError(f"Tavily search failed: {exc}") from exc
        hits: list[RawHit] = []
        for r in data.get("results", []):
            hits.append(
                RawHit(
                    title=r.get("title", "") or r.get("url", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", "") or "",
                    relevance=float(r.get("score", 0.0) or 0.0),
                    published_date=r.get("published_date"),
                )
            )
        return [h for h in hits if h.url]

    def extract(self, urls: list[str]) -> dict[str, str]:
        if not urls:
            return {}
        try:
            resp = self._http.post(
                f"{self._base}/extract",
                json={
                    "api_key": self._key,
                    "urls": urls,
                    "extract_depth": "advanced",
                    "format": "text",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise SearchError(f"Tavily extract failed: {exc}") from exc
        out: dict[str, str] = {}
        for r in data.get("results", []):
            text = r.get("raw_content") or r.get("content") or ""
            if r.get("url") and text:
                out[r["url"]] = text
        return out


# ---------------------------------------------------------------------------
# Deterministic mock client over the fixture corpus
# ---------------------------------------------------------------------------
class MockSearchClient:
    """Offline stand-in: keyword-matches the query against the fixture corpus.

    Deterministic by construction — same query, same hits, every run — which
    is what makes the end-to-end tests and the zero-key demo trustworthy.
    """

    name = "mock-fixtures"

    def __init__(self, corpus: list[dict] | None = None):
        self._corpus = corpus if corpus is not None else CORPUS

    def _score(self, query: str, doc: dict) -> float:
        qwords = content_words(query)
        if not qwords:
            return 0.0
        keys = set(doc.get("keywords", []))
        title_words = content_words(doc["title"])
        body_words = content_words(doc["content"])
        score = 0.0
        for w in qwords:
            if w in keys:
                score += 3.0
            if w in title_words:
                score += 2.0
            if w in body_words:
                score += 0.5
        return score / (3.0 * len(qwords))  # normalise toward 0..1

    def search(self, query: str, max_results: int = 5) -> list[RawHit]:
        scored = [(self._score(query, d), d) for d in self._corpus]
        scored.sort(key=lambda sd: (-sd[0], sd[1]["url"]))  # stable, deterministic
        hits = [
            RawHit(
                title=d["title"],
                url=d["url"],
                snippet=d["content"][:240],
                relevance=round(min(1.0, s), 4),
                published_date=d.get("published_date"),
            )
            for s, d in scored
            if s >= 0.10  # incidental single-word matches are search noise
        ]
        if not hits:  # unmatched topic: fall back to the general AI/agent docs
            hits = [
                RawHit(
                    title=d["title"],
                    url=d["url"],
                    snippet=d["content"][:240],
                    relevance=0.1,
                    published_date=d.get("published_date"),
                )
                for d in self._corpus
                if "agent" in d.get("keywords", [])
            ]
        return hits[:max_results]

    def extract(self, urls: list[str]) -> dict[str, str]:
        by_url = {d["url"]: d["content"] for d in self._corpus}
        return {u: by_url[u] for u in urls if u in by_url}
