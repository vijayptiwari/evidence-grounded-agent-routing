# Public claim ledger

This ledger separates what the project demonstrates from what it proposes. It is intended to keep the paper, repository, portfolio, and launch material aligned.

## Claim 1: the artifact is an integrated decision-provenance design

The project contributes a concrete engineering composition: a Routing Decision Record joins source-linked candidate evidence, eligibility decisions, versioned evaluators, calibrated uncertainty, rejected alternatives, explicit non-selection outcomes, a bounded delegation contract, and a separately measured execution outcome.

Evidence available in this repository: the white paper, JSON Schemas, executable reference implementation, worked examples, replay support, and tests.

Allowed wording: “proposes,” “designs,” “implements,” or “integrates.” Avoid “the first” or “uniquely solves” unless a separately documented novelty review supports that statement.

## Claim 2: the design is executable

The reference path, optional LangGraph parallel and single-agent dispatch paths, and privacy-minimized Langfuse adapter have been physically exercised. Exact replay, integrity-failure detection, schema conformance, and benchmark generation are covered by automated checks.

Allowed wording: “implemented and tested in the included reference environment.” This does not imply production hardening, general reliability, or compatibility with every future dependency version.

## Claim 3: the synthetic benchmark differentiates design variants

On the included 30-case synthetic development evaluation, the full configuration achieved `0.9667` route-decision accuracy and zero measured constraint violations. Several baselines and ablations performed worse on selected metrics.

This result verifies the harness and exposes behavior on authored examples. The implementation and dataset were developed together, so the result is contaminated and cannot estimate population performance or establish superiority over external routers.

Allowed wording: “synthetic smoke-test result.” Do not call it independent, held-out, production, statistically confirmatory, or state of the art.

## Claim 4: richer records may improve root-cause analysis

This is a falsifiable hypothesis, not a measured result. The randomized crossover protocol in `experiments/rca-protocol.md` defines how to compare selected-path traces with full decision records using diagnosis accuracy, time, confidence, and evidence use.

Allowed wording: “designed to support RCA” or “hypothesized to reduce diagnosis effort.” Do not say the framework reduces RCA time until that study is completed.

## Claim 5: “evidence-grounded” is the current maturity label

The design requires evidence attribution and exposes its basis for inspection. The current agent capabilities and priors are synthetic or self-asserted, and no independently collected production outcome study has been completed.

“Evidence-based routing” is the target claim for a future release only after preregistered, reproducible evaluation on independently collected and appropriately governed data.

## Promotion gate for stronger claims

Before strengthening any public claim, record the research question, protocol, frozen implementation and data versions, provenance and privacy review, labeling process, baselines, primary metrics, uncertainty analysis, subgroup checks, negative results, and limitations. Link the resulting evidence from this ledger and update all public copy in the same pull request.
