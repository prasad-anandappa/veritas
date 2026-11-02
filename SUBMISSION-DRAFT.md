# Veritas — ODSC × Nebius Hackathon submission draft

**Project name:** Veritas
**Repo:** https://github.com/prasad-anandappa/veritas
**Author:** Prasad Dimba Anandappa (@prasad-anandappa)
**Built with:** Nebius Token Factory · Tavily · FastAPI · Python

## One-liner

A research agent that turns a question into a sourced report — then verifies every claim against the source it cites, and flags anything it cannot prove.

## Description

Veritas decomposes a question into sub-questions, searches the live web with Tavily (search + full-text extraction), deduplicates and quality-scores the sources (relevance, domain authority, recency), and synthesises a cited answer with open models served by Nebius Token Factory. Its defining step is the one most research tools skip: an independent **verification pass** that checks every drafted claim three ways — the citation must resolve to a retrieved source, the claim's key terms must actually appear in that source's text (a deterministic floor no model can talk past), and a model entailment check must agree the source supports the claim. Claims that fail any leg are excluded from the answer and shown, with reasons, in a flagged list.

The result is a report where citation is an enforced invariant, not a formatting choice: every claim cited, every citation resolvable, every claim verified — asserted in code on every run and covered by 48 tests.

It runs end-to-end today with zero setup in a deterministic offline mock mode (bundled fixture corpus + deterministic LLM stages — same code paths), and switches to live Tavily + Token Factory by setting two API keys. Web UI, REST API, and a Markdown CLI included.

## Demo script (for the video)

1. Open the UI, ask the solid-state batteries example; show the step feed (plan → search → extract → score → verify) and the cited answer with support scores.
2. Open the Sources table: quality scores, dates, dedup at work.
3. Show a flagged claim (test_verification.py / an unsupported question): the agent would rather flag than fabricate.
4. Show `/api/health` in mock mode, then with keys set — same code, live backends.
