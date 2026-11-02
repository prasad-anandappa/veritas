"""Command-line interface: ask a question, get a cited Markdown report.

Usage:
    python -m app.cli "What is the current state of solid-state batteries?"
"""
from __future__ import annotations

import sys

from .agent import ResearchAgent
from .config import load_settings
from .models import ResearchReport


def render_markdown(report: ResearchReport) -> str:
    mode = report.mode.upper()
    lines = [
        f"# {report.question}",
        "",
        f"*Veritas · mode: {mode} · search: {report.search_backend} · "
        f"llm: {report.llm_backend}*",
        "",
        report.summary,
        "",
    ]
    for section in report.sections:
        lines.append(f"## {section.heading}")
        lines.append("")
        for claim in section.claims:
            cites = " ".join(f"[{c}]" for c in claim.citations)
            lines.append(f"- {claim.text} {cites}")
        lines.append("")
    if report.flagged_claims:
        lines += ["## Flagged — excluded from the answer", ""]
        for claim in report.flagged_claims:
            lines.append(f"- ~~{claim.text}~~ — {claim.note}")
        lines.append("")
    lines += ["## Sources", ""]
    for src in report.sources:
        date = f", {src.published_date}" if src.published_date else ""
        lines.append(
            f"- [{src.id}] {src.title} — {src.url} "
            f"(quality {src.quality:.2f}{date})"
        )
    lines += [
        "",
        f"*{report.stats.claims_verified} verified claims · "
        f"{report.stats.claims_flagged} flagged · "
        f"{report.stats.sources_used} sources cited of "
        f"{len(report.sources)} retrieved-and-scored*",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    question = " ".join(argv).strip()
    report = ResearchAgent(load_settings()).run(question)
    print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
