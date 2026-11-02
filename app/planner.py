"""Query planning: turn one question into a small set of sub-questions.

Two implementations behind one function signature:
  * ``llm_plan`` — asks the LLM (Nebius Token Factory in live mode) for a
    JSON list of sub-questions, validates it, and falls back on any problem.
  * ``rule_plan`` — deterministic decomposition used by the mock LLM and as
    the universal fallback. It never fails and never returns an empty plan.
"""
from __future__ import annotations

import re

from .textutil import content_words

_FILLER = re.compile(
    r"^(what|how|why|when|where|which|who|is|are|do|does|did|can|could|should|"
    r"tell me about|explain|describe|give me|please)\b[\s:,-]*",
    re.IGNORECASE,
)


def topic_of(question: str) -> str:
    """Extract the topic phrase from a question, deterministically."""
    q = question.strip().rstrip("?.!")
    previous = None
    while previous != q:  # peel stacked filler prefixes ("What is the ...")
        previous = q
        q = _FILLER.sub("", q).strip()
        q = re.sub(r"^(the|a|an)\s+", "", q, flags=re.IGNORECASE)
    q = re.sub(r"\s+", " ", q)
    return q or question.strip().rstrip("?.!")


def rule_plan(question: str, max_sub: int = 4) -> list[str]:
    """Deterministic decomposition into complementary research angles."""
    topic = topic_of(question)
    low = question.lower()
    subs: list[str] = [topic]

    if " vs " in low or " versus " in low or "compare" in low or "difference" in low:
        subs.append(f"{topic} — head-to-head comparison of evidence")
    if any(w in low for w in ("current", "state", "status", "latest", "today", "now")):
        subs.append(f"{topic} — latest developments and current status")
    subs.append(f"{topic} — key evidence, data and findings")
    subs.append(f"{topic} — challenges, limitations and criticism")
    subs.append(f"{topic} — outlook, forecasts and what happens next")

    # Dedupe (case-insensitive), preserve order, cap.
    seen: set[str] = set()
    plan: list[str] = []
    for s in subs:
        key = " ".join(sorted(content_words(s)))
        if key not in seen and s.strip():
            seen.add(key)
            plan.append(s)
    return plan[:max_sub]


def validate_plan(raw: object, question: str, max_sub: int = 4) -> list[str] | None:
    """Validate untrusted LLM plan output; None means 'use the fallback'."""
    if not isinstance(raw, list):
        return None
    plan: list[str] = []
    for item in raw:
        if isinstance(item, str) and 8 <= len(item.strip()) <= 300:
            plan.append(item.strip())
    if len(plan) < 2:
        return None
    return plan[:max_sub]
