# ADR 002 — Custom agent loop instead of a framework

- **Status:** accepted
- **Date:** 2026-11-10
- **Context change:** `foundation-and-first-slice`

## Context

The agent must run a multi-step loop (model → tool → result → model) with typed tools, hard limits, guardrails (citation enforcement, schema validation, escalation), and per-case memory. We could adopt a framework (e.g. LangChain) or write our own loop on top of the Anthropic SDK.

A central goal of the project is to **demonstrate understanding of the agent harness itself** — not to look like an LLM wrapper. The evaluation system also needs precise control over every step to measure tool-selection accuracy, citation faithfulness, and cost per step.

## Decision

Write a **custom agent loop** on top of the Anthropic SDK. No agent framework.

- The loop, step/timeout/token limits, tool registry, and guardrails are our own code.
- Tools are deterministic functions with Pydantic schemas; the LLM only selects which to call.
- Guardrails (discard uncited claims, validate schema, escalate denials/low-confidence) are enforced in code, not in prompts.

## Consequences

- **Pro:** full control and observability over every step — essential for the evals and for root-cause debugging. Nothing hidden behind framework abstractions.
- **Pro:** the harness is itself portfolio evidence of applied-AI engineering judgment.
- **Con:** we implement loop mechanics (retries, limits, tracing hooks) ourselves instead of getting them for free.
- **Con:** more upfront code before the first end-to-end case runs.

## When we would change our mind

If the loop grows enough that maintaining our own orchestration outweighs the control it gives, we would evaluate a framework as a comparison — and document that comparison (with evals) rather than switching blind.
