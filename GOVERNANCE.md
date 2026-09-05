# Project governance

Evidence-Grounded Agent Routing is currently maintained as a single-maintainer research project. The maintainer makes release decisions and is responsible for ensuring that accepted changes preserve the project’s stated evidence and safety boundaries.

## Decision process

Material changes should begin with a GitHub issue and be resolved through a reviewed pull request. The issue should state the problem, proposed change, alternatives considered, expected evidence, and compatibility impact. The final rationale should remain visible in the issue or pull request history.

The maintainer may reject a change that is operationally useful but weakens provenance, bypasses eligibility controls, conflates raw scores with probabilities, hides non-selection outcomes, or creates an unsupported research claim.

## Versioning

The Python package follows semantic versioning from `0.1.0`. During the `0.x` period, minor releases may contain breaking changes when they are called out in the changelog and migration notes.

Record formats have their own `schema_version`. A breaking schema change requires a new schema version, updated examples and tests, and a documented migration path. Changing an evaluator, policy bundle, registry, calibration target, calibration cohort, or cost model must produce new provenance metadata even when the JSON shape is unchanged.

## Evidence and claim promotion

A development observation becomes a public empirical claim only after the relevant protocol, data origin, labels, exclusions, implementation version, metrics, and limitations are documented. Results obtained on the included synthetic development set remain smoke-test results regardless of their numeric value.

Security, compliance, safety, and “state of the art” claims require separate review and are never inferred from ordinary test passage.

## Changes requiring explicit review

- routing or abstention thresholds;
- eligibility, authorization, or policy behavior;
- collection or export of request content;
- evidence-source trust or freshness rules;
- benchmark cases, labels, splits, or primary metrics;
- schema compatibility or retention behavior; and
- wording that strengthens novelty, effectiveness, safety, or compliance claims.

As participation grows, this document should be revised to name additional maintainers, review quorum, conflict-resolution rules, and a succession process.
