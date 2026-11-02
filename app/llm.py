"""LLM clients behind one interface: plan / synthesize / verify.

``NebiusLLM`` talks to **Nebius Token Factory** — open-model inference over
its OpenAI-compatible Chat Completions API (raw HTTP via httpx, no vendor
SDK lock-in). ``MockLLM`` is fully deterministic and offline: rule-based
planning, *extractive* synthesis (claims are sentences lifted from the
sources themselves, so they are cited by construction) and lexical
verification. The agent treats both identically, and in live mode any LLM
failure falls back to the deterministic implementation for that stage —
the pipeline never dies because a model hiccuped.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

import httpx

from .models import Claim, Source
from .planner import rule_plan, validate_plan
from .textutil import containment, sentences


class LLMError(RuntimeError):
    pass


@dataclass
class ClaimDraft:
    text: str
    citations: list[str]


class LLMClient(Protocol):
    name: str

    def plan(self, question: str, max_sub: int = 4) -> list[str]: ...

    def synthesize(
        self, question: str, sub_question: str, sources: list[Source]
    ) -> list[ClaimDraft]: ...

    def verify(self, claim_text: str, excerpt: str) -> tuple[bool, float, str]: ...


# ---------------------------------------------------------------------------
# Deterministic mock LLM (offline; also the live-mode fallback)
# ---------------------------------------------------------------------------
class MockLLM:
    name = "mock-deterministic"

    def plan(self, question: str, max_sub: int = 4) -> list[str]:
        return rule_plan(question, max_sub=max_sub)

    def synthesize(
        self, question: str, sub_question: str, sources: list[Source]
    ) -> list[ClaimDraft]:
        """Extractive synthesis: the best-supported sentences become claims.

        Each claim is a verbatim sentence from one source, cited to that
        source — so the citation is correct by construction, and the
        verification pass then independently re-checks it.
        """
        drafts: list[ClaimDraft] = []
        seen: set[str] = set()
        focus = f"{question} {sub_question}"
        for src in sources[:3]:
            text = src.content or src.snippet
            ranked = sorted(
                sentences(text),
                key=lambda s: (-containment(s, focus + " " + src.title), s),
            )
            picked = 0
            for sent in ranked:
                if picked >= 2 or len(drafts) >= 5:
                    break
                key = sent.lower()
                if key in seen or len(sent.split()) < 7:
                    continue
                # Topicality gate: the sentence must actually be about the
                # sub-question (search noise retrieves off-topic pages too).
                # Concrete sentences (with numbers) get a lower bar — they
                # are the most verifiable ones.
                topicality = containment(sent, focus)
                has_number = any(ch.isdigit() for ch in sent)
                if topicality < (0.06 if has_number else 0.12):
                    continue
                seen.add(key)
                drafts.append(ClaimDraft(text=sent, citations=[src.id]))
                picked += 1
        return drafts

    def verify(self, claim_text: str, excerpt: str) -> tuple[bool, float, str]:
        score = containment(claim_text, excerpt)
        supported = score >= 0.55
        reason = (
            f"lexical support {score:.2f} "
            f"({'≥' if supported else '<'} 0.55 threshold)"
        )
        return supported, round(score, 4), reason


# ---------------------------------------------------------------------------
# Nebius Token Factory LLM (OpenAI-compatible)
# ---------------------------------------------------------------------------
_JSON_BLOCK = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


def _extract_json(text: str) -> object | None:
    match = _JSON_BLOCK.search(text or "")
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        return None


class NebiusLLM:
    """Open-model inference via Nebius Token Factory (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        http: httpx.Client | None = None,
        fallback: MockLLM | None = None,
    ):
        if not api_key:
            raise LLMError("NEBIUS_API_KEY / TOKEN_FACTORY_API_KEY is required")
        self._key = api_key
        self._base = base_url.rstrip("/")
        self._model = model
        self._http = http or httpx.Client(timeout=60.0, trust_env=False)
        self._fallback = fallback or MockLLM()
        self.name = f"nebius-token-factory:{model}"

    # -- raw chat -----------------------------------------------------------
    def chat(self, system: str, user: str) -> str:
        try:
            resp = self._http.post(
                f"{self._base}/chat/completions",
                headers={"Authorization": f"Bearer {self._key}"},
                json={
                    "model": self._model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"] or ""
        except Exception as exc:
            raise LLMError(f"Nebius Token Factory call failed: {exc}") from exc

    # -- pipeline stages ----------------------------------------------------
    def plan(self, question: str, max_sub: int = 4) -> list[str]:
        raw = self.chat(
            "You are a research planner. Reply with a JSON array of strings only.",
            f"Decompose this research question into {max_sub} complementary "
            f"sub-questions that together answer it fully. Each sub-question "
            f"must be independently searchable.\nQuestion: {question}",
        )
        plan = validate_plan(_extract_json(raw), question, max_sub=max_sub)
        if plan is None:
            raise LLMError("LLM plan failed validation")
        return plan

    def synthesize(
        self, question: str, sub_question: str, sources: list[Source]
    ) -> list[ClaimDraft]:
        if not sources:
            return []
        blocks = "\n\n".join(
            f"[{s.id}] {s.title} ({s.domain})\n{(s.content or s.snippet)[:1800]}"
            for s in sources
        )
        raw = self.chat(
            "You are a research analyst. Reply with a JSON object only, of the "
            'form {"claims": [{"text": "...", "citations": ["S1"]}]}. Every '
            "claim must be a single atomic factual statement supported by the "
            "sources, and must cite the source ids that support it. Never "
            "state anything the sources do not say.",
            f"Question: {question}\nSub-question: {sub_question}\n\n"
            f"Sources:\n{blocks}\n\nWrite 2-5 claims answering the sub-question.",
        )
        parsed = _extract_json(raw)
        valid_ids = {s.id for s in sources}
        drafts: list[ClaimDraft] = []
        if isinstance(parsed, dict):
            for item in parsed.get("claims", []):
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text", "")).strip()
                cites = [
                    c for c in item.get("citations", [])
                    if isinstance(c, str) and c in valid_ids
                ]
                if text and cites:  # uncited or mis-cited drafts never survive
                    drafts.append(ClaimDraft(text=text, citations=cites))
        if not drafts:
            raise LLMError("LLM synthesis produced no valid cited claims")
        return drafts[:5]

    def verify(self, claim_text: str, excerpt: str) -> tuple[bool, float, str]:
        raw = self.chat(
            "You are a strict fact-checker. Reply with a JSON object only: "
            '{"supported": true|false, "score": 0.0-1.0, "reason": "..."}. '
            "supported=true only if the excerpt directly supports the claim.",
            f"Claim: {claim_text}\n\nSource excerpt:\n{excerpt[:2500]}",
        )
        parsed = _extract_json(raw)
        if not isinstance(parsed, dict) or "supported" not in parsed:
            raise LLMError("LLM verification output failed validation")
        try:
            score = float(parsed.get("score", 1.0 if parsed["supported"] else 0.0))
        except (TypeError, ValueError):
            score = 1.0 if parsed["supported"] else 0.0
        return bool(parsed["supported"]), max(0.0, min(1.0, score)), str(
            parsed.get("reason", "")
        )[:200]
