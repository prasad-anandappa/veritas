"""Query planning: deterministic decomposition + LLM-plan validation."""
from app.planner import rule_plan, topic_of, validate_plan


def test_topic_extraction_strips_question_framing():
    topic = topic_of("What is the current state of solid-state batteries?")
    assert "solid-state batteries" in topic
    assert not topic.lower().startswith("what")


def test_topic_extraction_plain_question():
    assert "fusion" in topic_of("How close is fusion energy to powering the grid?").lower()


def test_rule_plan_covers_multiple_angles():
    plan = rule_plan("What is the current state of solid-state batteries for EVs?")
    assert 3 <= len(plan) <= 4
    joined = " ".join(plan).lower()
    assert "solid-state" in joined
    assert "challenges" in joined
    assert "latest developments" in joined  # question asked for "current state"


def test_rule_plan_comparison_question_gets_comparison_angle():
    plan = rule_plan("Compare solid-state batteries vs lithium-ion batteries")
    assert any("comparison" in p.lower() for p in plan)


def test_rule_plan_is_deterministic_and_capped():
    q = "Why do research agents need verification passes?"
    assert rule_plan(q) == rule_plan(q)
    assert len(rule_plan(q, max_sub=2)) == 2


def test_rule_plan_never_empty():
    assert len(rule_plan("Fusion?")) >= 1
    assert len(rule_plan("???")) >= 1


def test_validate_plan_accepts_good_llm_output():
    raw = ["sub question one here", "sub question two here", "third sub question"]
    assert validate_plan(raw, "q") == raw


def test_validate_plan_rejects_garbage():
    assert validate_plan("not a list", "q") is None
    assert validate_plan([], "q") is None
    assert validate_plan(["only one valid", 42, None], "q") is None
    assert validate_plan([{"text": "dicts are not strings"}] * 3, "q") is None


def test_validate_plan_caps_length():
    raw = [f"sub question number {i} here" for i in range(9)]
    assert len(validate_plan(raw, "q", max_sub=4)) == 4
