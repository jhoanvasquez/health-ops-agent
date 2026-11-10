# Architecture

## Overview

The Health Operations Agent is a prior-authorization assistant. A request enters through an API, is processed asynchronously by an agent worker, and produces a cited decision packet that a human reviews when confidence is low or the outcome is a denial.

```
                 ┌──────────────┐
  Request ─────► │  FastAPI API │ ──► Postgres (cases, state, audit log)
                 └──────┬───────┘
                        │ publishes event
                        ▼
                 ┌──────────────┐
                 │   RabbitMQ   │  (retries, dead-letter)
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐        ┌────────────────────┐
                 │ Agent Worker │ ─────► │ Tools:             │
                 │ (harness)    │        │  - get_patient     │
                 │  loop + mem  │        │  - search_policy   │
                 │  guardrails  │        │  - check_criterion │
                 └──────┬───────┘        │  - draft_decision  │
                        │                │  - request_info    │
                        │                └────────────────────┘
                        ▼
              ┌───────────────────┐
              │ Human review      │ ◄── UI (React): evidence + citations
              └───────────────────┘
                        │
              Langfuse (traces) + metrics
```

## Principles

- **The agent never decides alone** on low-confidence or denial cases — a human always reviews them. This is enforced in the harness, not the prompt.
- **Every step is audited:** which tool, what input, what output, what cost. The audit log is append-only.
- **Tools are deterministic, testable functions.** The LLM only decides which tool to use; the tool does the work.
- **Every clinical claim cites evidence** (`doc_id` + excerpt). Uncited claims are discarded.
- **Synthetic data only.** Zero real PHI anywhere in the system.

## Components

| Component | Responsibility |
|---|---|
| `app/api` | Accept and query cases. Thin: validate → enqueue/query. Creating a case publishes an event. |
| `app/agent` | The harness: bounded loop, typed tools, guardrails, versioned prompts, structured outputs. |
| `app/workers` | Consume queue events, run the agent, persist state + audit entries. |
| `app/db` | SQLAlchemy models and Alembic migrations (cases, audit, policy chunks). |
| `app/llm` | `LLMClient` interface + Anthropic adapter. Swappable for model comparison in evals. |
| `app/ingestion` | Parse policy PDFs with page references, chunk, and embed into pgvector. |
| `evals` | Versioned case dataset, metrics, and the eval harness that gates changes. |

## Data flow (first slice)

1. `POST /cases` validates the request, persists a `Case` in state `received`, and publishes a `case_id` event. Returns `202`.
2. The worker consumes the event, loads the case, and runs the agent loop.
3. The agent uses tools (`get_patient`, `search_policy`, …) to gather evidence and drafts a `DecisionPacket`.
4. Guardrails discard uncited claims and validate the schema; the escalation rule routes `deny` / low-confidence cases to `needs_human`.
5. The final state and packet are persisted; every step wrote an audit entry.

## Key decisions

See `docs/adr/`. Notably: **ADR 001** (stack and RabbitMQ) and **ADR 002** (a custom agent loop instead of a framework).
