# Plain LLM classifier baseline prompt

Use this prompt to generate an external baseline under a pinned model and inference configuration. Do not add the evidence-grounded fields to this baseline; the purpose is to compare against a conventional categorical router.

## System prompt

```text
You route requests among a supplied registry of agents.

Choose exactly one decision:
- select: one agent can handle the request;
- parallel: two or more agents are independently needed;
- clarify: the request is ambiguous or underspecified;
- abstain: no registered agent supports the request;
- escalate: the request explicitly requires policy or human review.

Return JSON only with these fields:
case_id, decision, selected_agents, ranked_candidates, probabilities.

selected_agents must be empty for clarify, abstain, or escalate.
probabilities maps agent IDs to estimated probabilities between zero and one.
Do not return an explanation or hidden reasoning.
```

## User payload

Provide:

```json
{
  "case_id": "test-001",
  "request": "<request text>",
  "context": {},
  "agent_registry": [
    {
      "agent_id": "billing-agent",
      "description": "...",
      "capabilities": ["..."]
    }
  ]
}
```

## Reproducibility requirements

Record the provider, exact model snapshot, system-prompt hash, registry hash, temperature, seed if supported, response schema, retry policy, timestamp, and any provider-side routing. Validate every row against [`schemas/external-prediction.schema.json`](../../schemas/external-prediction.schema.json).

Save one JSON object per test case, then run:

```bash
PYTHONPATH=src python -m egr benchmark \
  --external plain-llm=path/to/plain-llm-predictions.jsonl \
  --output benchmark/results/with-llm.json
```

An external learned router can use the same prediction contract. Training data must not include the final evaluation cases.
