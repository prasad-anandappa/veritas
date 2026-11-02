# 🔎 Veritas — the research agent that proves its answers

**Ask a question; get a sourced, verified report.** Veritas plans sub-questions, searches the live web, scores and deduplicates what it finds, synthesises an answer with open models — and then **checks every single claim against the source it cites** before showing it to you. Claims that fail verification are flagged and excluded from the answer, in the open. No uncited assertions, no citations that don't resolve, no quietly invented facts.

Built for the **ODSC × Nebius Hackathon** (submissions close Nov 20, 2026) on the mandatory stack: **Nebius Token Factory** (open-model inference, OpenAI-compatible API) for all reasoning, and **Tavily** for real-time web search and extraction.

---

## The problem

Language models answer fluently — and sometimes invent. Research tools that bolt citations on afterwards are barely better: studies of cited answers keep finding claims whose citations don't actually support them. A research agent is only trustworthy if citation is a *checked invariant*, not a formatting choice. Veritas is built around that invariant:

> **Every claim in a finished report carries at least one citation, every citation resolves to a source that was actually retrieved, and every claim has passed an independent verification check against that source's text.** The invariant is asserted in code on every report, and tested.

## How it works

```text
                        ┌──────────────────────────────────────────────┐
  Question ───────────► │ 1. PLAN     decompose into ≤4 sub-questions   │
                        │             (Nebius LLM, or deterministic     │
                        │              rules in mock mode)              │
                        └──────────────┬───────────────────────────────┘
                                       ▼
                        ┌──────────────────────────────────────────────┐
                        │ 2. SEARCH   Tavily /search per sub-question  │
                        │ 3. EXTRACT  Tavily /extract full text for    │
                        │             the top unique URLs              │
                        └──────────────┬───────────────────────────────┘
                                       ▼
                        ┌──────────────────────────────────────────────┐
                        │ 4. SCORE    URL-normalise + dedup (exact &   │
                        │             near-duplicate shingles), then   │
                        │             quality = relevance + domain     │
                        │             authority + recency → S1…Sn      │
                        └──────────────┬───────────────────────────────┘
                                       ▼
                        ┌──────────────────────────────────────────────┐
                        │ 5. SYNTHESISE  cited claims per sub-question │
                        │             (Nebius LLM instructed to state  │
                        │              only what sources say; claim    │
                        │              drafts with bad/no citations are │
                        │              discarded before verification)  │
                        └──────────────┬───────────────────────────────┘
                                       ▼
                        ┌──────────────────────────────────────────────┐
                        │ 6. VERIFY   each claim, independently:       │
                        │   a. citation exists & resolves              │
                        │   b. deterministic support floor — the       │
                        │      claim's key terms must appear in the    │
                        │      cited text (a model can't talk its way  │
                        │      past this)                              │
                        │   c. model entailment check with score +     │
                        │      reason                                  │
                        │   Fail anything → flagged list, never in     │
                        │   the answer.                                │
                        └──────────────┬───────────────────────────────┘
                                       ▼
                        Cited report (web UI · REST API · CLI Markdown)
```

| Layer | Tech |
|---|---|
| Agent core | Python, explicit pipeline stages (`plan → search → extract → score → synthesize → verify`), each emitting a UI-readable step |
| Inference | **Nebius Token Factory** — OpenAI-compatible Chat Completions over raw HTTP (no vendor SDK lock-in); default model `meta-llama/Llama-3.3-70B-Instruct`, any Token Factory model via `NEBIUS_MODEL` |
| Search | **Tavily** REST — `/search` (advanced depth) + `/extract` (full text, advanced) |
| Web | FastAPI + one self-contained HTML/CSS/JS page (no build step) |
| Verification | Deterministic lexical support floor **and** model entailment, plus citation-resolution checks |
| Tests | pytest — **48 tests**: planning, scoring/dedup, client wire formats, citation integrity, verification behaviour, full pipeline end-to-end over HTTP in mock mode |

## Quickstart (under 2 minutes, zero keys)

```bash
git clone https://github.com/prasad-anandappa/veritas.git
cd veritas
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000
```

Open **http://localhost:8000** — it runs immediately in **MOCK mode**: search serves a bundled fixture corpus and the LLM stages run deterministically (rule-based planning, extractive synthesis, lexical verification), so the *entire pipeline — including the verification pass — works offline with no credentials*. Try the example chips, or use the CLI:

```bash
.venv/bin/python -m app.cli "What is the current state of solid-state batteries for electric vehicles?"
```

### Switch to LIVE mode (real Tavily + real Nebius Token Factory)

Get a Tavily key at [tavily.com](https://tavily.com) and a Token Factory key at [tokenfactory.nebius.com](https://tokenfactory.nebius.com), then:

```bash
export TAVILY_API_KEY="tvly-…"
export NEBIUS_API_KEY="…"            # TOKEN_FACTORY_API_KEY also accepted
# optional: NEBIUS_MODEL=…  NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
```

Restart — **the same code paths** now search the live web and reason with open models on Token Factory. Each component switches independently; `/api/health` reports exactly which mode each is in (`mock` / `partial` / `live`). If a live LLM call fails or returns unusable output at any stage, that stage falls back to the deterministic implementation and the step feed says so — the pipeline degrades, it never dies.

**Honest note on mock vs live:** mock mode is a real pipeline run over *synthetic fixture documents* (hosted on `.example` domains in the corpus, written for this demo), not a recording of live output. It exists so judges can run everything with zero setup and so the test suite can be deterministic. The live path is the same code with real clients swapped in behind the same interfaces.

## Demo walkthrough (2 minutes)

1. **Ask** — click the solid-state batteries example chip and hit **Research it**. Watch the agent activity feed: 4 sub-questions → searches → extraction → 18 hits deduped/scored to a handful of sources.
2. **Read the answer** — every claim carries `[S#]` citation chips (hover for the source title, click to jump to it) and a ✓ support score from the verification pass.
3. **Check the receipts** — the Sources table shows each source's quality score (relevance + authority + recency) and date; the stats bar shows how many drafted claims passed verification.
4. **See the gate work** — ask a question the corpus can't support, or read the unit tests in `tests/test_verification.py`: fabricated claims, uncited claims, and claims citing non-existent sources are all **flagged with reasons and excluded**, never silently dropped or passed through.

## API

| Endpoint | What it does |
|---|---|
| `POST /api/research` | Full agent pipeline for `{"question": "…"}` → structured cited report |
| `GET /api/health` | Mode report (mock/partial/live, per-component backends) |
| `GET /api/examples` | Example questions |
| `GET /` | Web UI |

## Design decisions

- **Verification is a separate pass, not a prompt instruction.** Telling a model "only say supported things" is a hope; checking each claim afterwards — with a deterministic lexical floor a model cannot argue past, plus an entailment judgement — is a mechanism. Flagged claims stay visible with reasons: the failure mode is *transparency*, not silence.
- **Extractive mock synthesis.** In mock mode, claims are sentences lifted from the sources themselves, cited by construction, then *still* run through the same verification pass. The demo can therefore never show a claim the pipeline didn't check.
- **Clients behind interfaces, env-gated.** `SearchClient` and `LLMClient` protocols; real Tavily/Nebius implementations and deterministic mocks are interchangeable, selected purely by which env vars exist. The Nebius client is raw HTTP against the OpenAI-compatible endpoint — swap models with one env var.
- **Scoring before synthesis.** Dedup (exact-URL after normalisation, plus 5-word shingle near-duplicates) and quality scoring happen *before* the model sees anything, so duplicate pages can't crowd out independent evidence and the model works from the strongest sources first.
- **Per-sub-question source selection by topical overlap**, not just search provenance — one good source can serve several sub-questions, and search noise gets filtered twice.

## How it maps to the judging criteria

| Criterion (weight) | How Veritas answers it |
|---|---|
| Sourced / verifiable answers (30%) | The citation invariant (cited + resolvable + verified) is enforced in code and asserted per report; verification has three independent legs including a deterministic floor; flagged claims are shown with reasons |
| Works end-to-end (25%) | Full pipeline runs today in mock mode (UI, API, CLI) with 48 passing tests; live mode is the same code paths gated on two env vars |
| Usefulness (20%) | Real research questions decomposed and answered with dated, quality-scored sources; CLI Markdown output drops into notes/docs; per-claim support scores let readers triage trust |
| Agent design (15%) | Explicit staged agent (plan/search/extract/score/synthesize/verify) with per-stage fallbacks, step feed, dedup + scoring, and global claim dedup across sections |
| Token Factory + Tavily (10%) | Both are load-bearing: Tavily does all search + extraction, Token Factory does all planning/synthesis/entailment in live mode; health endpoint proves which backends are live |

## Tests

```bash
.venv/bin/python -m pytest -q   # 48 tests, all offline in mock mode
```

## Roadmap

Streaming progress in the UI · cross-source corroboration scoring (claims supported by 2+ independent sources ranked higher) · contradiction detection between sources · PDF/HTML export of reports · saved research sessions · source freshness alerts for recurring questions.

## Author

**Prasad Dimba Anandappa** — GitHub [@prasad-anandappa](https://github.com/prasad-anandappa)

## License

MIT — see [LICENSE](LICENSE).

*Built with AI-assisted development (Muse).*
