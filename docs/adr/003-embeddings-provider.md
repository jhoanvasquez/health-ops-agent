# ADR 003 — Embeddings provider

- **Status:** accepted
- **Date:** 2026-11-10
- **Context change:** `foundation-and-first-slice`

## Context

`search_policy` retrieves policy passages by semantic similarity, which requires
an embedding model. The database column is `Vector(1024)` (ADR 001 / the initial
migration), so the provider's dimensionality must match. We use Anthropic for the
agent LLM, but Anthropic does not offer an embeddings endpoint.

## Decision

Use **Voyage AI**, model **`voyage-3`** (1024 dimensions), behind the `Embedder`
port (`app/agent/tools/ports.py`).

- Voyage is the embeddings provider Anthropic officially recommends.
- `voyage-3` outputs 1024-dim vectors, matching the existing `PolicyChunk.embedding`
  column — no migration change needed.
- The adapter distinguishes `input_type` (`document` at ingestion, `query` at search)
  to improve retrieval quality.

Because retrieval sits behind the `Embedder` and `PolicyStore` ports, swapping the
provider later (or comparing providers in evals) touches only the adapter.

## Consequences

- A new external dependency (`voyageai`) and a `VOYAGE_API_KEY` secret.
- Ingestion and query must use the **same** model/dimension, or similarity breaks.
- Cost/latency of embedding is incurred at ingestion (once per chunk) and per search query.

## When we would change our mind

If retrieval quality is poor on real policies, or cost/latency matters, we would
benchmark alternatives (a larger Voyage model, or a local open model) using the
retrieval metrics in the eval harness, and record the comparison here.
