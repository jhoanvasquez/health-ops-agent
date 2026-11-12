"""Evaluation CLI.

Modes:
  python evals/run_evals.py --self-check        # deterministic, no network (CI gate)
  python evals/run_evals.py --model claude-haiku-4-5   # real model, real metrics
  python evals/run_evals.py --include-hidden     # also score the hidden subset

See ADR 004 for the CI-gating split.
"""

from __future__ import annotations

import argparse
import asyncio

from evals.dataset import load_cases
from evals.metrics import Metrics, aggregate
from evals.report import write_report
from evals.runner import CaseResult, LLMFactory, replay_llm_factory, run_dataset


def _anthropic_factory(model: str) -> LLMFactory:
    from app.llm.anthropic import AnthropicClient  # lazy: self-check needs no credentials

    client = AnthropicClient(model=model)
    return lambda case: client


def _print_table(metrics: Metrics, held_out: int) -> None:
    print("\n=== Evaluation metrics ===")
    print(f"cases scored:            {metrics.n}  (held out {held_out} hidden)")
    print(f"decision accuracy:       {metrics.decision_accuracy:.3f}")
    print(f"escalation accuracy:     {metrics.escalation_accuracy:.3f}")
    print(f"citation faithfulness:   {metrics.citation_faithfulness:.3f}")
    print(f"per-criterion accuracy:  {metrics.per_criterion_accuracy:.3f}")
    print(f"unsupported claims:      {metrics.unsupported_claims}")


def _self_check_passed(metrics: Metrics) -> bool:
    return (
        metrics.decision_accuracy == 1.0
        and metrics.escalation_accuracy == 1.0
        and metrics.citation_faithfulness == 1.0
        and metrics.per_criterion_accuracy == 1.0
        and metrics.unsupported_claims == 0
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the agent evaluation dataset.")
    parser.add_argument("--model", default="claude-haiku-4-5", help="model id for a real run")
    parser.add_argument("--self-check", action="store_true", help="deterministic, no network")
    parser.add_argument("--include-hidden", action="store_true", help="also score hidden cases")
    parser.add_argument("--report", action="store_true", help="write docs/eval-report.md (Phase 4)")
    args = parser.parse_args()

    cases = load_cases(include_hidden=args.include_hidden)
    held_out = len(load_cases(include_hidden=True)) - len(cases)

    llm_for = replay_llm_factory() if args.self_check else _anthropic_factory(args.model)
    model_label = "self-check (scripted)" if args.self_check else args.model
    results: list[CaseResult] = asyncio.run(run_dataset(cases, llm_for))
    metrics = aggregate([r.score for r in results])
    _print_table(metrics, held_out)

    if args.report:
        path = write_report(results, metrics, model_label)
        print(f"\nwrote {path}")

    if args.self_check:
        if metrics.n == 0:
            print("\nself-check: no cases in dataset yet (nothing to check)")
            return
        if not _self_check_passed(metrics):
            print("\nSELF-CHECK FAILED: the eval pipeline did not reproduce expected metrics")
            raise SystemExit(1)
        print("\nself-check OK")


if __name__ == "__main__":
    main()
