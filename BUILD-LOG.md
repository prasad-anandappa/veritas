# Veritas — Build Log

**Date:** 2026-11-02 · **Builder:** Muse (delegated build lane) · **Author:** Prasad Dimba Anandappa
**Context:** ODSC × Nebius Hackathon, submissions close Nov 20, 2026. Official challenge: a research agent that turns a question into a sourced, verifiable answer. Mandatory stack: Nebius Token Factory + Tavily. Quality bar: the InvoicePilot project standard (working code, real passing tests, judge-runnable README, MIT).

## What was built

Project name: **Veritas**. Architecture: Python + FastAPI + one self-contained web UI (same pattern as InvoicePilot), plus a CLI that renders the same report as Markdown. Justification: a research agent's value is a *readable, checkable report* — a small web UI makes citations clickable and the agent's steps visible to judges in seconds, while the API/CLI keep it composable.

| Piece | Path | Notes |
|---|---|---|
| Agent core | `app/agent.py` | 6 stages (plan, search, extract, score, synthesize, verify), each emitting UI-readable steps; per-stage deterministic fallbacks; citation invariant asserted on every report |
| Config | `app/config.py`, `.env.example` | `TAVILY_API_KEY`; `NEBIUS_API_KEY` / `TOKEN_FACTORY_API_KEY` (+ base URL / model aliases); per-component mock/live gating |
| Search clients | `app/search_client.py` | `TavilySearchClient` (real REST `/search` + `/extract`) + `MockSearchClient` (deterministic fixture corpus) behind one protocol |
| LLM clients | `app/llm.py` | `NebiusLLM` (Token Factory OpenAI-compatible chat completions, raw httpx; JSON-validated plan/synthesize/verify; invalid citations discarded pre-verification) + `MockLLM` (rule planner, extractive synthesis, lexical verifier) |
| Planner | `app/planner.py` | Deterministic decomposition (topic extraction, comparison/latest/challenges/evidence angles) + LLM-plan validation |
| Scoring | `app/scoring.py` | URL normalisation, exact + shingle near-dup dedup, composite quality (0.5 relevance + 0.3 domain authority + 0.2 recency) |
| Verification | `app/verification.py` | 3 legs: citation resolves → deterministic containment floor (≥0.25) → model entailment with score/reason; failures flagged with reasons, never reported |
| Fixtures | `app/fixtures.py` | 13 synthetic documents across 4 topics on `.example` domains — honest demo data, clearly not live sources |
| API + UI | `app/main.py`, `static/index.html` | `/api/research`, `/api/health`, `/api/examples`, UI with step feed, citation chips, support scores, flagged-claims panel, source quality table |
| CLI | `app/cli.py` | `python -m app.cli "question"` → cited Markdown report |
| Tests | `tests/` | planner (9), scoring (9), clients (9), citations (5), verification (7), pipeline/API (9) |

## Verification — tests

```
python3 -m pytest -q
48 passed in 0.99s   (Python 3.12.3)
```

## Verification — live mock flow (uvicorn on :8199, real curl calls)

1. **Health** → `{"ok":true,"mode":"mock","search":"mock-fixtures","llm":"mock-deterministic"}`
2. **Research** — `POST /api/research` with *"What is the current state of solid-state batteries for electric vehicles?"* →
   4 sub-questions · 18 hits retrieved → 5–6 scored sources after dedup · claims all verified with support 1.0 in extractive mock mode · steps: plan → search ×4 → extract → score → verify ×4.
3. **CLI** — all four bundled example questions (solid-state batteries, fusion, GLP-1, research-agent verification) produce clean, on-topic, fully cited Markdown reports; cross-topic search noise is retrieved but never cited (topical-overlap source selection + topicality gate in synthesis + global claim dedup were added after the first smoke run exposed exactly that failure).
4. **UI** — `GET /` → HTTP 200.
5. **Wire formats** — Tavily and Nebius clients are covered by MockTransport tests asserting request URL, auth header, and body shape, so the live integration is tested as far as possible without keys.

## Honest remaining gap

- **No live run yet**: this environment has no `TAVILY_API_KEY` or `NEBIUS_API_KEY` (account creation is handled outside this build lane). The live clients are implemented against the documented APIs (Token Factory base URL `https://api.tokenfactory.nebius.com/v1` confirmed from Nebius docs on 2026-11-02) and wire-format-tested, but a real end-to-end live run — and tuning the default model choice against the account's actual Token Factory catalog — remains to be done the moment keys land. Mock mode is fully verified and demo-ready in the meantime.
- **Submission form** (hackathon.odsc.ai / emailed participant link) is the parent's final web step; the repo is public and submittable as-is.
- Known mock-mode character: extractive synthesis means later sub-question sections can be thin when their best claims were already used by an earlier section (global dedup wins over repetition). Live LLM synthesis does not have this behaviour.

## Repo

https://github.com/prasad-anandappa/veritas (public, MIT)
