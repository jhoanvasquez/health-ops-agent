"""Render an evaluation report as Markdown — metrics plus a failure breakdown."""

from __future__ import annotations

from pathlib import Path

from evals.metrics import Metrics
from evals.runner import CaseResult

REPORT_PATH = Path("docs/eval-report.md")


def _miss_reasons(result: CaseResult) -> list[str]:
    score = result.score
    reasons: list[str] = []
    if not score.decision_correct:
        reasons.append("decision")
    if not score.escalation_correct:
        reasons.append("escalation")
    if score.unsupported > 0:
        reasons.append(f"{score.unsupported} unsupported citation(s)")
    if score.criteria_correct < score.criteria_total:
        reasons.append(f"criteria {score.criteria_correct}/{score.criteria_total}")
    return reasons


def render_report(results: list[CaseResult], metrics: Metrics, model: str) -> str:
    lines: list[str] = [
        "# Evaluation report",
        "",
        f"- **Model:** `{model}`",
        f"- **Cases scored:** {metrics.n}",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Decision accuracy | {metrics.decision_accuracy:.3f} |",
        f"| Escalation accuracy | {metrics.escalation_accuracy:.3f} |",
        f"| Citation faithfulness | {metrics.citation_faithfulness:.3f} |",
        f"| Per-criterion accuracy | {metrics.per_criterion_accuracy:.3f} |",
        f"| Unsupported claims | {metrics.unsupported_claims} |",
        "",
        "## Where it fails and why",
        "",
    ]

    misses = [r for r in results if _miss_reasons(r)]
    if not misses:
        lines.append("No misses on this run.")
    else:
        for result in misses:
            packet = result.result.packet
            actual_outcome = packet.outcome if packet is not None else "(no packet)"
            lines.append(f"### `{result.case.id}` — missed: {', '.join(_miss_reasons(result))}")
            lines.append("")
            lines.append(f"- tags: {', '.join(result.case.tags) or '—'}")
            lines.append(
                f"- expected: outcome `{result.case.expected.outcome}`, "
                f"state `{result.case.expected.state}`"
            )
            lines.append(f"- actual: outcome `{actual_outcome}`, state `{result.result.state}`")
            if packet is not None and packet.summary:
                lines.append(f"- agent summary: {packet.summary}")
            lines.append("")

    return "\n".join(lines) + "\n"


def write_report(
    results: list[CaseResult], metrics: Metrics, model: str, path: Path = REPORT_PATH
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(results, metrics, model), encoding="utf-8")
    return path
