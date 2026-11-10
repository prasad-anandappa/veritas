"""The Veritas research agent: question → sourced, verified answer.

Pipeline (each stage emits a UI-readable step, like a tool call):

    plan        decompose the question into sub-questions (LLM or rules)
    search      Tavily search per sub-question (live) or fixture corpus
    extract     full-text extraction for the top hits (Tavily /extract)
    score       dedup + authority/recency/relevance quality scoring
    synthesize  cited claims per sub-question (LLM or extractive mock)
    verify      every claim checked against its cited source excerpts;
                unsupported claims are flagged and excluded from the answer

The report invariant — every claim cited, every citation resolvable — is
re-checked on the finished report before it is returned.
"""
from __future__ import annotations

from .config import Settings
from .llm import LLMClient, MockLLM, NebiusLLM, OtariLLM
from .models import (
    AgentStep,
    Claim,
    ReportStats,
    ResearchReport,
    Section,
    Source,
)
from .scoring import dedupe_and_score
from .search_client import MockSearchClient, SearchClient, TavilySearchClient
from .textutil import content_words, tokens
from .verification import verify_drafts


def build_search_client(settings: Settings) -> SearchClient:
    if settings.search_live:
        return TavilySearchClient(settings.tavily_api_key)
    return MockSearchClient()


def build_llm(settings: Settings) -> LLMClient:
    if settings.otari_api_key:
        # Mozilla Otari gateway (otari.ai) — same stage interface, routed
        # through one OpenAI-compatible endpoint with provider:model ids.
        return OtariLLM(
            settings.otari_api_key, settings.otari_base_url, settings.otari_model
        )
    if settings.llm_live:
        return NebiusLLM(
            settings.nebius_api_key, settings.nebius_base_url, settings.nebius_model
        )
    return MockLLM()


class ResearchAgent:
    def __init__(
        self,
        settings: Settings,
        search: SearchClient | None = None,
        llm: LLMClient | None = None,
    ):
        self.settings = settings
        self.search = search or build_search_client(settings)
        self.llm = llm or build_llm(settings)
        self._mock_llm = MockLLM()

    # -- stages -------------------------------------------------------------
    def _plan(self, question: str, steps: list[AgentStep]) -> list[str]:
        try:
            plan = self.llm.plan(question, max_sub=self.settings.max_sub_questions)
            steps.append(
                AgentStep(
                    tool="plan",
                    detail=f"{len(plan)} sub-questions via {self.llm.name}",
                )
            )
            return plan
        except Exception as exc:
            plan = self._mock_llm.plan(question, max_sub=self.settings.max_sub_questions)
            steps.append(
                AgentStep(
                    tool="plan",
                    detail=f"LLM planning unavailable ({exc}); deterministic plan used",
                    status="fallback",
                )
            )
            return plan

    def _synthesize(
        self, question: str, sub_q: str, sources: list[Source], steps: list[AgentStep]
    ):
        try:
            drafts = self.llm.synthesize(question, sub_q, sources)
            return drafts
        except Exception as exc:
            steps.append(
                AgentStep(
                    tool="synthesize",
                    detail=f"LLM synthesis failed for one section ({exc}); extractive fallback used",
                    status="fallback",
                )
            )
            return self._mock_llm.synthesize(question, sub_q, sources)

    # -- main loop ------------------------------------------------------------
    def run(self, question: str) -> ResearchReport:
        settings = self.settings
        steps: list[AgentStep] = []

        plan = self._plan(question, steps)

        # Search per sub-question, keeping provenance.
        hits_with_context = []
        for sub_q in plan:
            hits = self.search.search(sub_q, max_results=settings.results_per_query)
            hits_with_context.extend((h, sub_q) for h in hits)
            steps.append(
                AgentStep(tool="search", detail=f"{len(hits)} hits for “{sub_q[:70]}”")
            )
        total_retrieved = len(hits_with_context)

        # Extract full text for the unique top URLs.
        unique_urls: list[str] = []
        for hit, _ in hits_with_context:
            if hit.url not in unique_urls:
                unique_urls.append(hit.url)
        try:
            extracted = self.search.extract(unique_urls[: settings.max_sources * 2])
            steps.append(
                AgentStep(
                    tool="extract",
                    detail=f"full text for {len(extracted)}/{len(unique_urls)} unique URLs",
                )
            )
        except Exception as exc:
            extracted = {}
            steps.append(
                AgentStep(
                    tool="extract",
                    detail=f"extraction failed ({exc}); snippets used as evidence text",
                    status="fallback",
                )
            )

        # Dedup + score; attach extracted text as the verification evidence.
        sources = dedupe_and_score(
            hits_with_context, max_sources=settings.max_sources
        )
        for src in sources:
            src.content = extracted.get(src.url) or src.snippet
        steps.append(
            AgentStep(
                tool="score",
                detail=(
                    f"{total_retrieved} hits → {len(sources)} unique scored sources "
                    f"after dedup (top quality {sources[0].quality if sources else 0:.2f})"
                ),
            )
        )
        sources_by_id = {s.id: s for s in sources}

        # Synthesize + verify, per sub-question.
        sections: list[Section] = []
        flagged_all: list[Claim] = []
        total_drafts = 0
        seen_claim_texts: set[str] = set()
        for sub_q in plan:
            relevant = self._relevant_sources(sources, question, sub_q)
            drafts = self._synthesize(question, sub_q, relevant, steps)
            # A claim drafted for two sub-questions is reported once.
            drafts = [
                d for d in drafts
                if d.text.strip().lower() not in seen_claim_texts
            ]
            seen_claim_texts.update(d.text.strip().lower() for d in drafts)
            total_drafts += len(drafts)
            verified, flagged = verify_drafts(drafts, sources_by_id, self.llm)
            if verified:
                sections.append(Section(heading=sub_q, claims=verified))
            flagged_all.extend(flagged)
            steps.append(
                AgentStep(
                    tool="verify",
                    detail=(
                        f"“{sub_q[:60]}”: {len(verified)} claims verified, "
                        f"{len(flagged)} flagged"
                    ),
                )
            )

        verified_claims = [c for s in sections for c in s.claims]
        summary = self._summarise(question, sections, flagged_all)
        report = ResearchReport(
            question=question,
            mode=settings.mode,
            search_backend=self.search.name,
            llm_backend=self.llm.name,
            summary=summary,
            sub_questions=plan,
            sections=sections,
            sources=sources,
            flagged_claims=flagged_all,
            stats=ReportStats(
                sources_retrieved=total_retrieved,
                sources_used=len({c for cl in verified_claims for c in cl.citations}),
                claims_total=total_drafts,
                claims_verified=len(verified_claims),
                claims_flagged=len(flagged_all),
                citation_coverage=(
                    round(len(verified_claims) / total_drafts, 4) if total_drafts else 0.0
                ),
            ),
            steps=steps,
        )
        assert report.citation_integrity(), "citation integrity invariant violated"
        return report

    # -- source selection per sub-question ------------------------------------
    @staticmethod
    def _relevant_sources(
        sources: list[Source], question: str, sub_q: str, k: int = 4
    ) -> list[Source]:
        """Rank sources for one sub-question by topical overlap, then quality.

        Search provenance alone is not enough (one source can serve several
        sub-questions, and search returns noise); this keeps each section
        grounded in sources that are actually about its sub-question.
        """
        focus = content_words(f"{question} {sub_q}")
        if not focus:
            return sources[:k]
        scored: list[tuple[float, float, Source]] = []
        for s in sources:
            words = set(tokens(f"{s.title} {s.content or s.snippet}"))
            overlap = len(focus & words) / len(focus)
            scored.append((overlap, s.quality, s))
        scored.sort(key=lambda t: (-t[0], -t[1], t[2].url))
        picked = [s for overlap, _, s in scored if overlap >= 0.15][:k]
        return picked or sources[:3]

    # -- summary --------------------------------------------------------------
    @staticmethod
    def _summarise(
        question: str, sections: list[Section], flagged: list[Claim]
    ) -> str:
        if not sections:
            return (
                "No claim survived verification for this question, so Veritas "
                "reports no answer rather than an unsupported one. Try "
                "rephrasing the question or running in live mode."
            )
        leads: list[str] = []
        for s in sections:
            if s.claims and s.claims[0].text not in leads:
                leads.append(s.claims[0].text)
        body = " ".join(leads[:3])
        tail = (
            f" In total {sum(len(s.claims) for s in sections)} claims passed "
            f"verification against their cited sources"
        )
        if flagged:
            tail += f", and {len(flagged)} unsupported claim(s) were flagged and excluded"
        return f"{body}{tail}."
