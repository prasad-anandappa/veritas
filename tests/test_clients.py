"""Client layer: env gating, mock determinism, live-client wire format."""
import httpx
import pytest

from app.agent import build_llm, build_search_client
from app.config import Settings
from app.llm import NebiusLLM
from app.search_client import MockSearchClient, TavilySearchClient


def test_factory_defaults_to_mock_without_keys():
    s = Settings()
    assert isinstance(build_search_client(s), MockSearchClient)
    assert build_llm(s).name == "mock-deterministic"
    assert s.mode == "mock"


def test_factory_selects_live_clients_with_keys():
    s = Settings(tavily_api_key="tvly-x", nebius_api_key="sk-x")
    assert isinstance(build_search_client(s), TavilySearchClient)
    assert isinstance(build_llm(s), NebiusLLM)
    assert s.mode == "live"


def test_partial_mode_when_only_one_key():
    assert Settings(tavily_api_key="tvly-x").mode == "partial"
    assert Settings(nebius_api_key="sk-x").mode == "partial"


def test_mock_search_is_deterministic_and_topical():
    client = MockSearchClient()
    a = client.search("solid-state batteries for electric vehicles", max_results=5)
    b = client.search("solid-state batteries for electric vehicles", max_results=5)
    assert [h.url for h in a] == [h.url for h in b]
    assert a and "Solid-State" in a[0].title
    assert all("solid" in (h.title + h.url).lower() for h in a)  # all on-topic


def test_mock_search_unmatched_topic_falls_back():
    hits = MockSearchClient().search("underwater basket weaving championships")
    assert hits  # never empty — the pipeline always has something to work with


def test_mock_extract_returns_full_text():
    client = MockSearchClient()
    hit = client.search("fusion plasma record", max_results=1)[0]
    out = client.extract([hit.url])
    assert len(out[hit.url]) > len(hit.snippet)


def _mock_transport(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_tavily_client_wire_format():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        import json as _json

        seen["body"] = _json.loads(request.content)
        if request.url.path == "/search":
            return httpx.Response(200, json={"results": [
                {"title": "A", "url": "https://a.example/1", "content": "snip",
                 "score": 0.8, "published_date": "2026-10-01"}]})
        return httpx.Response(200, json={"results": [
            {"url": "https://a.example/1", "raw_content": "full text here"}]})

    client = TavilySearchClient("tvly-test", http=_mock_transport(handler))
    hits = client.search("q", max_results=3)
    assert hits[0].title == "A" and hits[0].relevance == 0.8
    assert seen["body"]["api_key"] == "tvly-test"
    assert seen["body"]["query"] == "q"
    out = client.extract(["https://a.example/1"])
    assert out == {"https://a.example/1": "full text here"}


def test_nebius_client_wire_format_and_parsing():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"choices": [
            {"message": {"content": '["sub question alpha here", "sub question beta here"]'}}]})

    llm = NebiusLLM("sk-test", "https://api.tokenfactory.nebius.com/v1",
                    "meta-llama/Llama-3.3-70B-Instruct", http=_mock_transport(handler))
    plan = llm.plan("Any question?")
    assert plan == ["sub question alpha here", "sub question beta here"]
    assert seen["url"].endswith("/chat/completions")
    assert seen["auth"] == "Bearer sk-test"


def test_nebius_bad_plan_output_raises_for_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "no json"}}]})

    llm = NebiusLLM("sk-test", "https://x.example/v1", "m", http=_mock_transport(handler))
    with pytest.raises(Exception):
        llm.plan("Any question?")
