# ADR 001 — Stack and queue choice

- **Status:** accepted
- **Date:** 2026-11-10
- **Context change:** `foundation-and-first-slice`

## Context

We are building an autonomous prior-authorization assistant that must demonstrate: autonomous agents with tool use, orchestration and memory, an evaluation system, and a solid backend. The project is also a portfolio piece for Applied AI Engineer roles, so the stack should match what those roles ask for and what the author already operates at scale (high-throughput backends, message brokers).

## Decision

- **Language / API:** Python 3.12 + FastAPI + Pydantic v2 — strong typing, async, directly relevant to target roles.
- **LLM:** Anthropic API behind our own `LLMClient` interface, so we can swap providers and compare models in evals.
- **Database:** PostgreSQL + pgvector — one engine for relational data, agent state, and semantic policy search.
- **Queue:** **RabbitMQ**, not Redis Streams.
- **Cache / locks:** Redis (idempotency, rate limiting).

### Why RabbitMQ over Redis Streams

- Native retries, acknowledgements, and dead-letter exchanges — exactly the reliability primitives the Week-5 hardening needs, without hand-rolling them.
- Ties into the broker experience the project wants to demonstrate (ActiveMQ/Kafka background).
- The cost is one more service in `docker-compose`; acceptable for the reliability we get.

## Consequences

- `docker-compose` runs four services (API, Postgres, RabbitMQ, Redis). Slightly heavier local setup.
- Reliability work (retries, dead-letter) builds on RabbitMQ primitives rather than custom code.
- Model comparison is possible because the LLM sits behind an interface.

## When we would change our mind

If infrastructure overhead becomes a real obstacle to shipping and the reliability features are not yet needed, we would fall back to Redis Streams for the queue and revisit this ADR.
