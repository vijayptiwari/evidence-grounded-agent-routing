# Dataset card: synthetic routing benchmark 1.0

## Purpose

This dataset exercises the reference implementation and evaluation code. It is designed to expose routing lifecycle behavior—not to estimate deployment performance.

## Composition

- 42 English-language synthetic requests;
- 12 cases used to fit the one-dimensional calibrator and select its threshold;
- 30 development smoke-evaluation cases;
- six synthetic agents covering billing, orders, HR, security, network operations, and knowledge retrieval; and
- decision labels for selection, parallel fan-out, clarification, abstention, and escalation.

The cases include direct target requests, paraphrases, multi-intent inputs, ambiguous inputs, unsupported domains, security review, blocked agents, missing tools, unavailable agents, and prompt-injection-style instructions.

## Fields

- `case_id`: stable case identifier;
- `split`: `calibration` or `test`;
- `text`: synthetic request supplied to the router;
- `context`: operational and policy facts supplied to the router;
- `acceptable_agents`: evaluation label never supplied to the router; and
- `expected_decision`: evaluation label never supplied to the router.

## Label policy

- `select` requires exactly the labeled agent.
- `parallel` requires exact set equality with the labeled agents.
- `clarify`, `abstain`, and `escalate` require an empty selected-agent set and the exact decision type.
- Candidate calibration labels mark whether a candidate appears in `acceptable_agents`; this is only a proxy for the downstream-success target proposed in the paper.

## Known contamination

The implementation was developed while these cases were visible. Consequently, the `test` split is a software-development set, not an independent held-out research set. The reported confidence interval and McNemar calculations verify analysis code but are not confirmatory statistical evidence.

## Appropriate uses

- regression tests;
- adapter development;
- metric and ablation verification;
- demonstrations of policy, abstention, replay, and provenance behavior; and
- a template for constructing an independently governed dataset.

## Inappropriate uses

- claiming production accuracy or safety;
- selecting a production threshold;
- comparing commercial systems without independently collected cases;
- making subgroup or multilingual claims; or
- treating synthetic success priors as real agent-performance evidence.

## Required successor dataset

The publishable study needs requests sampled independently from the implementation team, privacy review, a frozen label guide, multiple expert annotators, adjudication, subgroup metadata where appropriate, a sealed final test set, downstream execution outcomes, and a declared handling policy for ambiguous labels.
