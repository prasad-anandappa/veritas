"""End-to-end: the full pipeline over HTTP in mock mode."""
from fastapi.testclient import TestClient

from app.cli import render_markdown
from app.main import app

client = TestClient(app)
Q = "What is the current state of solid-state batteries for electric vehicles?"


def test_health_reports_mock_mode():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["mode"] in ("mock", "partial", "live")  # env-dependent, shape-checked


def test_examples_endpoint():
    r = client.get("/api/examples")
    assert r.status_code == 200
    assert len(r.json()["examples"]) >= 3


def test_research_end_to_end():
    r = client.post("/api/research", json={"question": Q})
    assert r.status_code == 200
    report = r.json()
    assert report["question"] == Q
    assert len(report["sub_questions"]) >= 3
    assert len(report["sources"]) >= 4
    assert report["sections"], "expected at least one answer section"
    claims = [c for s in report["sections"] for c in s["claims"]]
    assert len(claims) >= 4
    source_ids = {s["id"] for s in report["sources"]}
    for c in claims:
        assert c["status"] == "verified"
        assert c["citations"] and all(cid in source_ids for cid in c["citations"])
    assert report["stats"]["claims_verified"] == len(claims)
    assert report["summary"]
    tools = {s["tool"] for s in report["steps"]}
    assert {"plan", "search", "extract", "score", "verify"} <= tools


def test_research_is_deterministic_in_mock_mode():
    a = client.post("/api/research", json={"question": Q}).json()
    b = client.post("/api/research", json={"question": Q}).json()
    claims_a = [c["text"] for s in a["sections"] for c in s["claims"]]
    claims_b = [c["text"] for s in b["sections"] for c in s["claims"]]
    assert claims_a == claims_b
    assert [s["url"] for s in a["sources"]] == [s["url"] for s in b["sources"]]


def test_research_other_topics():
    for q in (
        "How close is fusion energy to powering the grid?",
        "What are the benefits and risks of GLP-1 drugs for weight loss?",
    ):
        r = client.post("/api/research", json={"question": q})
        assert r.status_code == 200
        assert r.json()["sections"], q


def test_short_question_rejected():
    r = client.post("/api/research", json={"question": "Fusion?"})
    assert r.status_code == 422


def test_missing_question_rejected():
    assert client.post("/api/research", json={}).status_code == 422


def test_ui_page_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "Veritas" in r.text


def test_cli_markdown_rendering():
    from app.agent import ResearchAgent
    from app.config import Settings

    report = ResearchAgent(Settings()).run(Q)
    md = render_markdown(report)
    assert md.startswith("# " + Q)
    assert "## Sources" in md
    assert "[S1]" in md
