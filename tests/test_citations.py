"""Citation integrity: every claim cited, every citation resolvable."""
from app.agent import ResearchAgent
from app.config import Settings
from app.llm import MockLLM, NebiusLLM
from app.models import Source
import httpx


def _source(sid="S1", content="Solid-state cells reach 500 watt-hours per kilogram in pilot tests."):
    return Source(id=sid, title="T", url=f"https://x.example/{sid}", domain="x.example",
                  snippet=content, content=content)


def test_mock_synthesis_claims_are_cited_by_construction():
    llm = MockLLM()
    drafts = llm.synthesize("q?", "solid-state batteries evidence", [_source()])
    assert drafts
    for d in drafts:
        assert d.citations == ["S1"]


def test_report_citation_integrity_e2e():
    report = ResearchAgent(Settings()).run(
        "What is the current state of solid-state batteries for electric vehicles?"
    )
    assert report.citation_integrity()
    ids = {s.id for s in report.sources}
    for claim in report.all_claims():
        assert claim.citations, "uncited claim in report"
        assert all(c in ids for c in claim.citations)
        assert claim.status == "verified"


def test_nebius_synthesis_drops_claims_with_unknown_citations():
    def handler(request: httpx.Request) -> httpx.Response:
        content = (
            '{"claims": ['
            '{"text": "Solid-state cells reach 500 watt-hours per kilogram.", "citations": ["S1"]},'
            '{"text": "A claim citing a source that was never retrieved.", "citations": ["S99"]},'
            '{"text": "An uncited claim that must not survive.", "citations": []}'
            "]}"
        )
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    llm = NebiusLLM("sk", "https://x.example/v1", "m",
                    http=httpx.Client(transport=httpx.MockTransport(handler)))
    drafts = llm.synthesize("q?", "sub?", [_source()])
    assert len(drafts) == 1
    assert drafts[0].citations == ["S1"]


def test_every_source_in_report_has_unique_id_and_url():
    report = ResearchAgent(Settings()).run("How close is fusion energy to powering the grid?")
    ids = [s.id for s in report.sources]
    urls = [s.url for s in report.sources]
    assert len(ids) == len(set(ids))
    assert len(urls) == len(set(urls))


def test_sources_cited_stat_matches_claims():
    report = ResearchAgent(Settings()).run(
        "What are the benefits and risks of GLP-1 drugs for weight loss?"
    )
    cited = {c for claim in report.all_claims() for c in claim.citations}
    assert report.stats.sources_used == len(cited)
    assert report.stats.claims_verified == len(report.all_claims())
    assert report.stats.claims_total == (
        report.stats.claims_verified + report.stats.claims_flagged
    )
