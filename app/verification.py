"""The verification pass — what makes Veritas more than a summariser.

Every drafted claim is checked, independently of how it was produced:

1. **Citation existence** — a claim with no citations, or a citation that
   does not resolve to a retrieved source, is flagged and never reported.
2. **Deterministic support floor** — the claim's own content words must
   actually appear in the cited sources' text (containment ≥ 0.25). This
   guard cannot be talked out of its verdict by a confident model.
3. **Model entailment check** — the LLM (Nebius in live mode, the lexical
   verifier in mock mode) judges whether the cited excerpt *supports* the
   claim, with a score and a reason.

A claim is reported only if it passes all three. Everything else lands in
``flagged_claims`` with the reason — visible in the UI, never silently
swept away, and never presented as part of the answer.
"""
from __future__ import annotations

from .llm import ClaimDraft, LLMClient, MockLLM
from .models import Claim, Source
from .textutil import containment

SUPPORT_FLOOR = 0.25


def verify_drafts(
    drafts: list[ClaimDraft],
    sources_by_id: dict[str, Source],
    llm: LLMClient,
) -> tuple[list[Claim], list[Claim]]:
    """Returns (verified claims, flagged claims) for one section's drafts."""
    verified: list[Claim] = []
    flagged: list[Claim] = []
    fallback = MockLLM()

    for draft in drafts:
        claim = Claim(text=draft.text, citations=list(draft.citations))

        if not draft.citations:
            claim.status, claim.note = "flagged", "no citation — dropped from the answer"
            flagged.append(claim)
            continue
        missing = [c for c in draft.citations if c not in sources_by_id]
        if missing:
            claim.status = "flagged"
            claim.note = f"citation(s) {missing} do not resolve to a retrieved source"
            flagged.append(claim)
            continue

        excerpt = "\n".join(
            (sources_by_id[c].content or sources_by_id[c].snippet)
            for c in draft.citations
        )
        floor = containment(draft.text, excerpt)
        if floor < SUPPORT_FLOOR:
            claim.status = "flagged"
            claim.support = round(floor, 4)
            claim.note = (
                f"fails deterministic support floor (containment {floor:.2f} "
                f"< {SUPPORT_FLOOR}) — the cited source does not contain the "
                "claim's key terms"
            )
            flagged.append(claim)
            continue

        try:
            supported, score, reason = llm.verify(draft.text, excerpt)
        except Exception:
            supported, score, reason = fallback.verify(draft.text, excerpt)
            reason = f"deterministic fallback verifier: {reason}"

        claim.support = round(score, 4)
        if supported:
            claim.status = "verified"
            claim.note = reason
            verified.append(claim)
        else:
            claim.status = "flagged"
            claim.note = f"not supported by its cited source: {reason}"
            flagged.append(claim)

    return verified, flagged
