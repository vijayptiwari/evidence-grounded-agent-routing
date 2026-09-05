# Controlled routing-RCA study protocol

Status: preregistration-ready draft. No participants have been recruited and no results are claimed.

## Research question

Does a structured Routing Decision Record help engineers identify the correct cause of an agent-routing incident faster and more accurately than a conventional selected-path trace?

## Hypotheses

- H1: RDR access reduces median time to a correct root-cause classification.
- H2: RDR access increases correct root-cause classifications.
- H3: RDR access increases agreement between reviewers.
- H4: Benefits are largest for prompt drift, registry drift, policy conflicts, and candidate-retrieval failures.

## Experimental design

Use a randomized, counterbalanced crossover study. Each participant investigates incidents in both conditions, but never sees the same incident twice.

- **Control:** request reference, selected agent, selected execution trace, and final failure.
- **Treatment:** the same material plus candidate retrieval, rejected candidates, source-linked evidence, eligibility results, configuration versions, thresholds, and decision reason codes.

Construct at least 24 incidents across six failure classes:

1. candidate omitted by retrieval;
2. stale or poisoned capability entry;
3. prompt/model version drift;
4. policy or availability gate failure;
5. ambiguous request forced into a route; and
6. correct route followed by execution failure.

Randomize incident order and condition assignment. Counterbalance difficulty and failure class. Remove labels that directly reveal the injected cause.

## Participants

Recruit engineers with agent-platform, backend, SRE, ML, or production-support experience. Record experience bands before randomization. A pilot should estimate variance and inform sample size; do not choose the final sample size after observing treatment effects.

## Primary outcomes

- elapsed seconds to a submitted diagnosis;
- correct failure-class identification against the incident construction key; and
- correct identification of the component and version responsible.

## Secondary outcomes

- reviewer confidence on a fixed scale;
- number of trace or record fields inspected;
- number of hypothesis revisions;
- inter-reviewer agreement; and
- a short workload score.

## Analysis

- Compare paired completion times with a distribution-appropriate paired method and report median differences with bootstrap confidence intervals.
- Analyze diagnosis correctness with a paired categorical test or mixed-effects logistic model if participant and incident effects are modeled.
- Report effects by failure class and experience band as exploratory unless powered in advance.
- Include incomplete and timed-out investigations under a declared policy.
- Publish anonymized study materials and analysis code where permitted.

## Validity threats

- Synthetic incidents may be easier and cleaner than production failures.
- Participants may learn the RDR structure during the study.
- Extra information can improve performance simply through volume; the control should contain comparable irrelevant detail where practical.
- Tool familiarity and domain knowledge may dominate the treatment.
- Faster diagnosis does not prove safer routing.

## Exit criterion

The white paper may state that the RDR improved RCA only if the preregistered primary outcome succeeds and the effect remains practically meaningful. Otherwise report the null or adverse result and revise the framework.
