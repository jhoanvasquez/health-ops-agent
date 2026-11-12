# Evaluation report

- **Model:** `claude-haiku-4-5`
- **Cases scored:** 6

## Metrics

| Metric | Value |
|---|---|
| Decision accuracy | 0.833 |
| Escalation accuracy | 0.833 |
| Citation faithfulness | 1.000 |
| Per-criterion accuracy | 0.923 |
| Unsupported claims | 0 |

## Where it fails and why

### `04-low-confidence-ambiguous-policy` — missed: decision, escalation, criteria 0/1

- tags: low-confidence, ambiguous-policy, escalation
- expected: outcome `approve`, state `needs_human`
- actual: outcome `request_info`, state `request_info`
- agent summary: The policy requires an 'adequate trial of conservative management' but does not define the minimum duration. The patient completed 4 weeks of conservative management with partial (not complete) improvement. The policy explicitly does not address partial improvement outcomes. This ambiguity prevents a high-confidence determination. Additional clinical guidance is needed on: (1) whether 4 weeks meets the 'adequate' threshold, and (2) whether partial improvement satisfies the policy's intent for conservative management trial.

