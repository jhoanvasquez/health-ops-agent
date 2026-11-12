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
# generate a synthetic policy PDF that matches the patient-001 fixture
python data/make_sample_policy.py

docker compose up -d --build

# ingest the policy into pgvector (run inside the worker: it has the DB + data volume)
docker compose exec worker \
  python -m app.ingestion.ingest_cli data/policies/sample-policy.pdf sample-policy policy-doc-1

# submit a synthetic case (patient fixture lives in data/patients/)
curl -X POST localhost:8000/cases -H 'content-type: application/json' \
  -d '{"idempotency_key":"demo-1","policy_id":"sample-policy","patient_ref":"patient-001"}'

# poll for the decision (use the case_id from the response above)
curl localhost:8000/cases/<case_id>
```

### End-to-end test

With the stack up, a policy ingested, and the patient fixture in place:

```bash
RUN_INTEGRATION=1 pytest tests/integration -q
```

### Evaluation

The agent is scored against a versioned dataset of synthetic cases (`evals/cases/`)
on decision accuracy, citation faithfulness, correct escalation, and per-criterion
accuracy — with no database or embedding API (fixtures). See `docs/eval-report.md`
for the baseline.

```bash
python evals/run_evals.py --self-check             # deterministic; the CI gate
python evals/run_evals.py --model claude-haiku-4-5 --report   # real metrics + report
```

## Reliability

Case processing is resilient. When the worker fails on a case (a transient LLM/API
error, a DB hiccup), the message is retried with a delay through a dead-letter
topology, up to 3 attempts. After that the case is marked `failed` (with a redacted
`last_error`) and its message lands in a durable `cases.dead` queue for inspection.
A message whose body cannot be parsed is dead-lettered on the first delivery.

**Queue recreation.** The main queue `cases.process` carries dead-letter arguments.
On an older broker where it was declared without them, RabbitMQ rejects the
changed-argument re-declare — recreate with a clean broker:

```bash
docker compose down        # or: down -v to also wipe data
docker compose up -d
```

**Inspect the dead-letter queue.** RabbitMQ management UI at http://localhost:15672
(credentials from `.env`) → Queues → `cases.dead`.

**See it in action.** Point the worker at an invalid model so every attempt fails,
then watch a case retry and land in `cases.dead`:

```bash
# set LLM_MODEL to a bogus id in .env, then:
docker compose up -d --force-recreate worker
curl -X POST localhost:8000/cases -H 'content-type: application/json' \
  -d '{"idempotency_key":"fail-demo","policy_id":"sample-policy","patient_ref":"patient-001"}'
docker compose logs -f worker     # 3 attempts, then dead-letter; the case ends `failed`
```

## License

TBD.
