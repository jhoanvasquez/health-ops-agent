# Healthcare Operations Agent — Prior Authorization Assistant

An autonomous agent that drafts prior-authorization decisions for healthcare operations, with its own agent harness, typed tools, mandatory human review, and an evaluation system.

> **Status:** early development. Not production. Uses **synthetic data only** — zero real PHI.

## The problem

Prior authorization is a slow, manual, error-prone step in healthcare: a clinician's request is checked, criterion by criterion, against a payer's policy. This agent assists that review.

Given a synthetic FHIR patient, clinical notes, and a payer policy (PDF), the agent:

1. Extracts the relevant clinical data.
2. Retrieves the applicable policy and its criteria.
3. Evaluates each criterion, **citing evidence** from the record and policy.
4. Drafts a decision packet: **approve / deny / request more information**.
5. **Escalates to a human reviewer** when confidence is low or information is missing.

A human always reviews denials and low-confidence cases. The agent never decides those alone.

## Architecture

```
Request ─► FastAPI ─► Postgres (cases, state, audit)
               │ publishes event
               ▼
           RabbitMQ (retries, dead-letter)
               ▼
        Agent Worker (loop + memory + guardrails)
               │   tools: get_patient · search_policy ·
               │          check_criterion · draft_decision · request_info
               ▼
        Human review UI (evidence + citations)  —  Langfuse traces + metrics
```

Every step is audited (which tool, what input, what output, what cost). Tools are deterministic, testable functions; the LLM only decides which one to call.

## Stack

Python 3.12 · FastAPI · Anthropic API (behind a swappable `LLMClient`) · custom agent loop · PostgreSQL + pgvector · SQLAlchemy 2 + Alembic · RabbitMQ · Redis · Synthea · Langfuse · Docker Compose · GitHub Actions.

## Evaluation

A versioned dataset of synthetic cases with expected outcomes and evidence drives the evals: decision accuracy, per-criterion accuracy, citation faithfulness, escalation rate, hallucination rate, tool-selection accuracy, and cost/latency. Evals run in CI and gate prompt/tool/model changes.

## Compliance note

This project uses synthetic data only. For a real production deployment you would additionally need: a BAA with the LLM provider, encryption at rest and in transit, role-based access control, data retention/deletion policies, and full audit logging. (Colombia analogy: Law 1581 / habeas data.)

## Development

```bash
cp .env.example .env         # fill in ANTHROPIC_API_KEY and VOYAGE_API_KEY
pip install -e ".[dev]"      # local tooling
ruff check . && mypy app evals scripts && pytest   # the CI gate
```

### Run the full slice

`docker compose up` starts everything: it applies migrations (one-shot `migrate`
service), then brings up the API, the agent worker, Postgres (pgvector), RabbitMQ,
and Redis.

```bash
docker compose up --build

# load a payer policy PDF (synthetic / non-PHI only) into pgvector
python -m app.ingestion.ingest_cli path/to/policy.pdf sample-policy policy-doc-1

# submit a synthetic case (patient fixture lives in data/patients/)
curl -X POST localhost:8000/cases -H 'content-type: application/json' \
  -d '{"idempotency_key":"demo-1","policy_id":"sample-policy","patient_ref":"patient-001"}'

# poll for the decision
curl localhost:8000/cases/<case_id>
```

### End-to-end test

With the stack up, a policy ingested, and the patient fixture in place:

```bash
RUN_INTEGRATION=1 pytest tests/integration -q
```

> The evaluation harness (`evals/`) is the next change — a versioned case dataset
> with accuracy, citation-faithfulness, escalation, and tool-selection metrics.

## License

TBD.
