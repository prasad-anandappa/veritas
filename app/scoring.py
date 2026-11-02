"""Source quality scoring and deduplication.

Retrieved hits become report sources only after:
  1. URL normalisation + exact-URL dedup (tracking params, fragments,
     trailing slashes and ``www.`` differences collapse to one source),
  2. near-duplicate content dedup (5-word shingle Jaccard ≥ 0.75), and
  3. composite quality scoring = relevance + domain authority + recency,
     so the report cites the strongest version of the evidence first.
"""
from __future__ import annotations

from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Source
from .search_client import RawHit
from .textutil import jaccard, shingles

_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                    "utm_content", "fbclid", "gclid", "ref", "source"}

# Domain authority tiers — primary/official and established outlets first.
_AUTHORITY_EXACT = {
    "gov": 1.0, "edu": 0.95,
}
_AUTHORITY_SUFFIXES = (
    (".gov", 1.0), (".edu", 0.95), (".gov.uk", 0.98), (".ac.uk", 0.93),
    (".org", 0.7), (".example", 0.6),
)
_KNOWN_STRONG = {
    "nature.com", "science.org", "nih.gov", "who.int", "iea.org",
    "reuters.com", "apnews.com", "bbc.com", "nytimes.com", "ft.com",
}


def domain_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    query = urlencode(
        [(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in _TRACKING_PARAMS]
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower() or "https", host, path, query, ""))


def authority_score(domain: str) -> float:
    if domain in _KNOWN_STRONG:
        return 0.95
    tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
    if tld in _AUTHORITY_EXACT:
        return _AUTHORITY_EXACT[tld]
    for suffix, score in _AUTHORITY_SUFFIXES:
        if domain.endswith(suffix):
            return score
    return 0.5  # ordinary .com / unknown


def recency_score(published_date: str | None, today: date | None = None) -> float:
    """1.0 for today, decaying to ~0.15 at 3+ years old; unknown date = 0.4."""
    if not published_date:
        return 0.4
    try:
        published = date.fromisoformat(published_date[:10])
    except ValueError:
        return 0.4
    today = today or date.today()
    age_days = max(0, (today - published).days)
    if age_days <= 30:
        return 1.0
    if age_days >= 1095:
        return 0.15
    return round(1.0 - 0.85 * (age_days - 30) / 1065, 4)


def quality_score(relevance: float, authority: float, recency: float) -> float:
    return round(0.5 * relevance + 0.3 * authority + 0.2 * recency, 4)


def dedupe_and_score(
    hits_with_context: list[tuple[RawHit, str]],
    max_sources: int = 12,
    today: date | None = None,
) -> list[Source]:
    """hits_with_context: (hit, sub_question it was retrieved for).

    Returns scored Sources with ids S1..Sn in quality order.
    """
    # 1) exact-URL dedup — keep the highest-relevance copy
    by_url: dict[str, tuple[RawHit, str]] = {}
    for hit, sub_q in hits_with_context:
        key = normalize_url(hit.url)
        if key not in by_url or hit.relevance > by_url[key][0].relevance:
            by_url[key] = (hit, sub_q)

    # 2) near-duplicate content dedup via shingles of snippet+title
    kept: list[tuple[RawHit, str]] = []
    kept_shingles: list[set] = []
    for hit, sub_q in sorted(
        by_url.values(), key=lambda hs: (-hs[0].relevance, hs[0].url)
    ):
        sh = shingles(f"{hit.title} {hit.snippet}")
        if any(jaccard(sh, other) >= 0.75 for other in kept_shingles):
            continue
        kept.append((hit, sub_q))
        kept_shingles.append(sh)

    # 3) score, sort by quality, assign ids
    sources: list[Source] = []
    for hit, sub_q in kept:
        domain = domain_of(hit.url)
        auth = authority_score(domain)
        rec = recency_score(hit.published_date, today=today)
        sources.append(
            Source(
                id="",  # assigned below
                title=hit.title,
                url=hit.url,
                domain=domain,
                snippet=hit.snippet,
                published_date=hit.published_date,
                sub_question=sub_q,
                relevance=round(hit.relevance, 4),
                authority=auth,
                recency=rec,
                quality=quality_score(hit.relevance, auth, rec),
            )
        )
    sources.sort(key=lambda s: (-s.quality, s.url))
    sources = sources[:max_sources]
    for i, s in enumerate(sources, start=1):
        s.id = f"S{i}"
    return sources
