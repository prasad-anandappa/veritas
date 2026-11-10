"""Otari gateway backend: factory selection, env gating, wire format, and
a full pipeline run spoken over the gateway's OpenAI-compatible surface
(httpx MockTransport — no network, no token needed)."""
import json
import re

import httpx
import pytest

from app.agent import ResearchAgent, build_llm
from app.config import Settings, load_settings
from app.llm import LLMError, MockLLM, NebiusLLM, OtariLLM
from app.search_client import MockSearchClient


def _mock_transport(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


# -- factory / config ---------------------------------------------------------

def test_factory_selects_otari_with_otari_key():
    llm = build_llm(Settings(otari_api_key="tk_x"))
    assert isinstance(llm, OtariLLM)
    assert llm.name == "otari:groq:llama-3.3-70b-versatile"


def test_factory_otari_takes_precedence_over_nebius():
    s = Settings(otari_api_key="tk_x", nebius_api_key="sk-y")
    assert s.llm_backend == "otari"
    assert isinstance(build_llm(s), OtariLLM)


def test_factory_nebius_and_mock_unchanged_without_otari_key():
    assert isinstance(build_llm(Settings(nebius_api_key="sk-y")), NebiusLLM)
    assert isinstance(build_llm(Settings()), MockLLM)


def test_otari_settings_report_in_mode_detail():
    s = Settings(tavily_api_key="tvly-x", otari_api_key="tk_x")
    assert s.mode == "live"
    assert s.mode_detail()["llm"] == "otari:groq:llama-3.3-70b-versatile"
    assert Settings(otari_api_key="tk_x").mode == "partial"


def test_otari_env_loading_and_aliases(monkeypatch):
    for var in ("OTARI_API_KEY", "OTARI_AI_TOKEN", "OTARI_BASE_URL", "OTARI_MODEL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OTARI_AI_TOKEN", "tk_alias")
    s = load_settings()
    assert s.otari_api_key == "tk_alias"
    assert s.otari_base_url == "https://api.otari.ai/v1"
    assert s.otari_model == "groq:llama-3.3-70b-versatile"

    monkeypatch.setenv("OTARI_API_KEY", "tk_primary")
    monkeypatch.setenv("OTARI_MODEL", "mistral:mistral-large-latest")
    monkeypatch.setenv("OTARI_BASE_URL", "https://gw.example/v1/")
    s = load_settings()
    assert s.otari_api_key == "tk_primary"  # OTARI_API_KEY wins over the alias
    assert s.otari_model == "mistral:mistral-large-latest"
    assert s.otari_base_url == "https://gw.example/v1"  # trailing slash stripped


def test_otari_requires_a_token():
    with pytest.raises(LLMError, match="OTARI_API_KEY"):
        OtariLLM("", "https://api.otari.ai/v1", "groq:llama-3.3-70b-versatile")


# -- wire format ---------------------------------------------------------------

def test_otari_wire_format_and_plan_parsing():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [
            {"message": {"content": '["sub question alpha here", "sub question beta here"]'}}]})

    llm = OtariLLM("tk_test", "https://api.otari.ai/v1",
                   "groq:llama-3.3-70b-versatile", http=_mock_transport(handler))
    assert llm.plan("Any question?") == [
        "sub question alpha here", "sub question beta here"]
    assert seen["url"] == "https://api.otari.ai/v1/chat/completions"
    assert seen["auth"] == "Bearer tk_test"
    # The gateway routes on the provider:model string — passed verbatim.
    assert seen["body"]["model"] == "groq:llama-3.3-70b-versatile"


def test_otari_bad_output_raises_for_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "no json"}}]})

    llm = OtariLLM("tk_test", "https://api.otari.ai/v1", "m",
                   http=_mock_transport(handler))
    with pytest.raises(LLMError):
        llm.plan("Any question?")


def test_otari_http_error_names_the_gateway():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad token"})

    llm = OtariLLM("tk_bad", "https://api.otari.ai/v1", "m",
                   http=_mock_transport(handler))
    with pytest.raises(LLMError, match="Otari gateway"):
        llm.plan("Any question?")


# -- end-to-end over the gateway surface ---------------------------------------

def _gateway_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    user = body["messages"][-1]["content"]
    if "Decompose this research question" in user:
        content = json.dumps([
            "What are solid-state batteries for electric vehicles?",
            "When will solid-state batteries reach electric vehicles?",
        ])
    elif "Write 2-5 claims" in user:
        # Echo one verbatim sentence from the first source block and cite
        # it — a claim the deterministic floor can independently confirm.
        m = re.search(r"\[(S\d+)\][^\n]*\n(.+)", user, re.DOTALL)
        sid, block = m.group(1), m.group(2)
        sentence = next(
            s.strip() for s in re.split(r"(?<=[.!?])\s+", block)
            if len(s.split()) >= 8
        )
        content = json.dumps({"claims": [{"text": sentence, "citations": [sid]}]})
    elif user.startswith("Claim:"):
        content = json.dumps({
            "supported": True, "score": 0.93,
            "reason": "the excerpt states this directly",
        })
    else:  # pragma: no cover - defensive
        content = "{}"
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_pipeline_end_to_end_through_otari_backend():
    llm = OtariLLM("tk_test", "https://api.otari.ai/v1",
                   "groq:llama-3.3-70b-versatile",
                   http=_mock_transport(_gateway_handler))
    agent = ResearchAgent(
        Settings(otari_api_key="tk_test"),
        search=MockSearchClient(),
        llm=llm,
    )
    report = agent.run("How do solid-state batteries work in electric vehicles?")
    assert report.llm_backend.startswith("otari:")
    assert report.stats.claims_verified >= 1
    assert report.citation_integrity()
    assert all(c.status == "verified" for s in report.sections for c in s.claims)
