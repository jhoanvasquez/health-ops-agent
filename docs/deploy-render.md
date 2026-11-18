# Deploy to Render — Runbook

One-time setup to put the full stack on a public URL. The infrastructure is declared in
[`render.yaml`](../render.yaml); this runbook covers the manual steps that can't live in
the repo — connecting the account, entering secrets, and the first-deploy wiring.

> **You run these steps.** They need your Render account and your API keys; there is no
> repo access to them, and there must not be — **no secret is ever committed.**

## Prerequisites

- A [Render](https://render.com) account with the GitHub repo connected.
- A [CloudAMQP](https://www.cloudamqp.com) account (free "Little Lemur" plan) — Render
  has no managed RabbitMQ, so the broker lives here.
- Your `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY`.

## 1. Create the CloudAMQP broker

1. In CloudAMQP, create a new instance → plan **Little Lemur (free)**.
2. Open the instance → copy its **AMQP URL** (`amqps://user:pass@host/vhost`).
3. Keep it handy — it becomes `RABBITMQ_URL` in step 3.

The app's `aio_pika.connect_robust` speaks `amqps` (TLS) with no code change.

## 2. Create the Blueprint

1. Render Dashboard → **New** → **Blueprint**.
2. Select this repository. Render reads `render.yaml` and shows the plan: `health-api`,
   `health-web`, `health-db` (Postgres 16), `health-redis`.
3. **Apply**. Render provisions the database and the Key Value store first, then builds
   the services.

> **No separate worker.** Render's free tier has no background-worker service type, so
> the API co-hosts the queue consumer in-process (`EMBED_WORKER=true`). On a paid plan,
> flip it to `false` and add a dedicated `type: worker` service.

## 3. Enter the secrets (once)

The three secrets live in the **`health-secrets`** env group — enter them one time and
the API picks them up:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic key |
| `VOYAGE_API_KEY` | your Voyage key |
| `RABBITMQ_URL` | the CloudAMQP `amqps://…` URL from step 1 |

`DATABASE_URL` and `REDIS_URL` are wired automatically from the managed services — leave
them alone.

## 4. First deploy

On startup, the API container runs `alembic upgrade head` before `uvicorn` — this
creates the schema (including `CREATE EXTENSION vector`) on every deploy (the migration
is idempotent). The free tier has no separate pre-deploy step, so it lives in the start
command. Watch the deploy logs:

- `health-db` → healthy.
- `health-api` → migrations succeed, `/health` returns `200`, and the log shows
  `consumer started, consuming cases.process` (the in-process worker connected to
  CloudAMQP).

If the log shows a broker connection error instead of `consumer started`, re-check
`RABBITMQ_URL` in `health-secrets`.

## 5. Wire the cross-origin URLs

Two values are only known after the first deploy — set them, then redeploy the affected
service:

1. **`VITE_API_URL`** on `health-web` → the `health-api` public URL
   (e.g. `https://health-api.onrender.com`). It's baked in at **build time**, so after
   setting it, trigger a redeploy of `health-web`.
2. **`CORS_ORIGINS`** on `health-api` → the `health-web` public URL **as a JSON array**:
   `["https://health-web.onrender.com"]`. (It's typed `list[str]`; a bare string won't
   parse.) Redeploy `health-api`.

## 6. Seed a policy and verify

The agent needs at least one ingested policy to evaluate against. The free tier has **no
shell**, so ingest over HTTP — `POST /policies` accepts a PDF upload, chunks it by page,
embeds it, and stores it. Generate the synthetic sample on your own machine, then upload:

```bash
# on your machine — build the synthetic policy PDF
python data/make_sample_policy.py

# upload it to the deployed API (multipart: policy_id, doc_id, file)
curl -X POST https://health-api.onrender.com/policies \
  -F policy_id=sample-policy \
  -F doc_id=policy-doc-1 \
  -F file=@data/policies/sample-policy.pdf
# -> {"policy_id":"sample-policy","doc_id":"policy-doc-1","chunks":N}
```

> The API process runs the embedding synchronously, so a very large PDF could approach
> the request timeout. The synthetic sample is small; it returns in a second or two.

Then submit a synthetic case against the public API and poll for the cited decision:

```bash
curl -X POST https://health-api.onrender.com/cases \
  -H 'content-type: application/json' \
  -d '{"idempotency_key":"demo-1","policy_id":"sample-policy","patient_ref":"patient-001"}'

curl https://health-api.onrender.com/cases/<case_id>
```

Open the review UI at the `health-web` URL — the escalated case should appear with its
cited evidence, ready for approve / deny / request-info.

## 7. (Optional) Custom domain

Render → `health-web` (and `health-api`) → **Settings → Custom Domains**. After pointing
a domain, update `VITE_API_URL` and `CORS_ORIGINS` to the new hosts and redeploy.

---

## Notes & limits

- **Free tier sleeps.** Render free web services spin down when idle; the first request
  after a nap is slow. Fine for a demo — not for production.
- **CloudAMQP free limits** (connections, message rate) are generous for a demo; the
  retry/dead-letter topology is unchanged.
- **Static `VITE_API_URL` is build-time.** Changing the API host later needs a rebuild
  of `health-web`, not just an env edit.
- This is still an engineering demo. A real deployment adds a BAA, encryption at rest,
  RBAC, retention/deletion, and audit logging — see the README's compliance section.
