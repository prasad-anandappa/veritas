"""Source scoring + dedup: URL normalisation, authority, recency, near-dupes."""
from datetime import date

from app.scoring import (
    authority_score,
    dedupe_and_score,
    domain_of,
    normalize_url,
    quality_score,
    recency_score,
)
from app.search_client import RawHit

TODAY = date(2026, 11, 2)


def hit(url, title="T", snippet="some unique snippet text here", rel=0.5, date_=None):
    return RawHit(title=title, url=url, snippet=snippet, relevance=rel, published_date=date_)


def test_normalize_url_strips_tracking_and_www():
    a = normalize_url("https://www.Example.com/path/?utm_source=x&b=1#frag")
    b = normalize_url("https://example.com/path?b=1")
    assert a == b


def test_domain_of_strips_www():
    assert domain_of("https://www.nature.com/articles/x") == "nature.com"


def test_authority_tiers():
    assert authority_score("energy.gov") == 1.0
    assert authority_score("mit.edu") >= 0.9
    assert authority_score("nature.com") >= 0.9
    assert authority_score("random-blog.com") == 0.5
    assert authority_score("energy.gov") > authority_score("random-blog.com")


def test_recency_decays_with_age():
    assert recency_score("2026-11-01", today=TODAY) == 1.0
    assert recency_score("2020-01-01", today=TODAY) < 0.3
    assert recency_score(None, today=TODAY) == 0.4
    assert recency_score("not-a-date", today=TODAY) == 0.4


def test_quality_is_weighted_composite():
    assert quality_score(1.0, 1.0, 1.0) == 1.0
    assert quality_score(0.0, 0.0, 0.0) == 0.0
    assert quality_score(1.0, 0.0, 0.0) == 0.5  # relevance dominates


def test_dedupe_collapses_same_url_variants():
    hits = [
        (hit("https://a.example/x?utm_campaign=z", rel=0.4), "q"),
        (hit("https://www.a.example/x/", rel=0.9), "q"),
    ]
    sources = dedupe_and_score(hits, today=TODAY)
    assert len(sources) == 1
    assert sources[0].relevance == 0.9  # kept the stronger copy


def test_dedupe_collapses_near_duplicate_content():
    text = " ".join(f"word{i}" for i in range(40))
    hits = [
        (hit("https://a.example/1", snippet=text, rel=0.9), "q"),
        (hit("https://b.example/2", snippet=text + " word40", rel=0.8), "q"),
        (hit("https://c.example/3", snippet="completely different material altogether", rel=0.7), "q"),
    ]
    sources = dedupe_and_score(hits, today=TODAY)
    assert len(sources) == 2


def test_ids_assigned_in_quality_order():
    hits = [
        (hit("https://weak.example/a", snippet="a weak little blog post about things", rel=0.1), "q"),
        (hit("https://energy.gov/b", snippet="an official laboratory report with data", rel=0.95, date_="2026-10-30"), "q"),
    ]
    sources = dedupe_and_score(hits, today=TODAY)
    assert [s.id for s in sources] == ["S1", "S2"]
    assert sources[0].domain == "energy.gov"
    assert sources[0].quality > sources[1].quality


def test_max_sources_cap():
    hits = [(hit(f"https://s{i}.example/p{i}", snippet=f"unique text number {i} here ok", rel=0.5), "q") for i in range(20)]
    assert len(dedupe_and_score(hits, max_sources=5, today=TODAY)) == 5
