# ADR 004 — Evaluation CI gating

- **Status:** accepted
- **Date:** 2026-11-11
- **Context change:** `evaluation-system`

## Context

The plan wants evals to gate merges: *"a prompt or model change that drops a key
metric blocks the merge."* The eval harness runs cases against the real agent and
compares to expected answers. Because the dataset uses a fixture policy store, the
only external dependency is the Anthropic LLM — no Voyage, no database.

Two forces pull against a strict real-model gate on every PR:

- **Non-determinism.** A real LLM varies run to run. On a small subset, a correct
  change can occasionally dip below a hard threshold and block a good merge.
- **Credentials & cost.** A real-model gate needs `ANTHROPIC_API_KEY` as a CI
  secret and spends (small) money on every PR.

## Decision

Split evaluation into two modes with two different jobs.

- **Merge gate (default, blocking): deterministic self-check.**
  `python evals/run_evals.py --self-check` runs the harness with a scripted
  `ReplayLLM` (fixture `LLMClient`) that returns fixed `draft_decision` packets.
  No network, no secret, no cost. It gates the **eval code and the harness
  plumbing** — loader, fixture context, metrics, report — so a regression in the
  evaluation machinery blocks the merge.

- **Real-model eval (opt-in, non-blocking by default).**
  `python evals/run_evals.py --model claude-haiku-4-5 --report` runs the dataset
  against the live model and produces `docs/eval-report.md`. Run locally for the
  baseline, or as a manually-triggered / secrets-gated CI job.

## Consequences

- Every PR gets a free, fast, non-flaky gate on the evaluation code itself.
- Real metrics are produced deliberately (local or opt-in job), where their
  natural variance is read as a number, not a pass/fail on a noisy threshold.
- The baseline report is a committed artifact, updated when the author runs it —
  not silently regenerated on every PR.

## When we would change our mind

Once the dataset is large enough (dozens of cases) that aggregate metrics are
stable run-to-run, promote the real-model eval to a **blocking** gate on PRs that
touch prompts, tools, or the model — with a threshold set below observed variance.
At that point the self-check remains as the fast pre-check.
