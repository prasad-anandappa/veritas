"""Verification pass: supported claims pass, fabricated ones are flagged."""
from app.llm import ClaimDraft, MockLLM
from app.models import Source
from app.textutil import containment
from app.verification import verify_drafts

EXCERPT = (
    "Pilot production lines began shipping sample cells to carmakers in 2026. "
    "The best sample cells reach an energy density of about 500 watt-hours "
    "per kilogram, roughly double a conventional lithium-ion cell."
)


def _sources():
    src = Source(id="S1", title="T", url="https://x.example/1", domain="x.example",
                 snippet=EXCERPT, content=EXCERPT)
    return {"S1": src}


def test_verbatim_supported_claim_is_verified():
    drafts = [ClaimDraft(
        text="The best sample cells reach an energy density of about 500 watt-hours per kilogram, roughly double a conventional lithium-ion cell.",
        citations=["S1"])]
    verified, flagged = verify_drafts(drafts, _sources(), MockLLM())
    assert len(verified) == 1 and not flagged
    assert verified[0].status == "verified"
    assert verified[0].support >= 0.55


def test_fabricated_claim_is_flagged():
    drafts = [ClaimDraft(
        text="Solid-state batteries are already installed in every passenger car sold in Europe and cost nine dollars each.",
        citations=["S1"])]
    verified, flagged = verify_drafts(drafts, _sources(), MockLLM())
    assert not verified and len(flagged) == 1
    assert flagged[0].note


def test_uncited_claim_is_flagged():
    drafts = [ClaimDraft(text="A claim with no citation at all attached to it.", citations=[])]
    verified, flagged = verify_drafts(drafts, _sources(), MockLLM())
    assert not verified and len(flagged) == 1
    assert "no citation" in flagged[0].note


def test_unresolvable_citation_is_flagged():
    drafts = [ClaimDraft(
        text="The best sample cells reach an energy density of about 500 watt-hours per kilogram.",
        citations=["S42"])]
    verified, flagged = verify_drafts(drafts, _sources(), MockLLM())
    assert not verified and len(flagged) == 1
    assert "do not resolve" in flagged[0].note


def test_claim_about_unrelated_topic_fails_support_floor():
    drafts = [ClaimDraft(
        text="The city council voted to repaint the bridge green next spring after a long public debate.",
        citations=["S1"])]
    verified, flagged = verify_drafts(drafts, _sources(), MockLLM())
    assert not verified and len(flagged) == 1
    assert "support floor" in flagged[0].note


def test_containment_scoring_behaviour():
    assert containment("sample cells reach 500 watt-hours per kilogram", EXCERPT) > 0.8
    assert containment("quantum gravity hologram teapot orchestra", EXCERPT) == 0.0


def test_flagged_claims_keep_their_citations_for_audit():
    drafts = [ClaimDraft(text="Completely invented statement about batteries flying to Mars.", citations=["S1"])]
    _, flagged = verify_drafts(drafts, _sources(), MockLLM())
    assert flagged[0].citations == ["S1"]
