"""Small deterministic text utilities shared by scoring and verification."""
from __future__ import annotations

import re

STOPWORDS = frozenset(
    """a an the and or but if then else of at by for with about into through during
    before after above below to from up down in out on off over under again further
    once here there when where why how all any both each few more most other some
    such no nor not only own same so than too very can will just is am are was were
    be been being have has had having do does did doing would should could ought i
    you he she it we they this that these those as its it's their his her our your
    my me him us them who whom what which also per via""".split()
)

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-]*")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


def tokens(text: str) -> list[str]:
    return _WORD_RE.findall((text or "").lower())


def content_words(text: str) -> set[str]:
    """Meaning-bearing words (no stopwords, length > 2, numbers kept)."""
    return {t for t in tokens(text) if t not in STOPWORDS and len(t) > 2 or t.isdigit()}


def sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_RE.split((text or "").strip())]
    return [p for p in parts if len(p) >= 20]


def containment(claim_text: str, excerpt: str) -> float:
    """Fraction of the claim's content words that appear in the excerpt.

    This is the deterministic floor of the verification pass: a claim whose
    own words barely appear in the source it cites cannot be supported by it.
    """
    claim_words = content_words(claim_text)
    if not claim_words:
        return 0.0
    excerpt_words = set(tokens(excerpt))
    hit = sum(1 for w in claim_words if w in excerpt_words)
    return hit / len(claim_words)


def shingles(text: str, n: int = 5) -> set[tuple[str, ...]]:
    toks = tokens(text)
    if len(toks) < n:
        return {tuple(toks)} if toks else set()
    return {tuple(toks[i : i + n]) for i in range(len(toks) - n + 1)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
