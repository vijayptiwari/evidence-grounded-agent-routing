# Evidence validity and sufficiency rubric

This rubric evaluates whether a routing record is auditable. It does not establish that every external claim is true.

## Evidence validity

An evidence item is structurally valid when:

- it has a stable evidence ID;
- its source family and source type are declared;
- `source_ref` resolves to an authorized source or protected content reference;
- the source and extraction method are versioned;
- the observation time is present;
- trust tier and freshness are declared;
- any quoted request span exists in the referenced request; and
- the raw value matches the output of the pinned extraction or measurement method.

An authenticated or signed source proves origin and integrity, not substantive truth. Truthfulness needs a separate verification procedure appropriate to the source type.

## Decision sufficiency

A selected candidate is minimally sufficient when the record contains:

1. an eligible policy result with a rule and policy-bundle version;
2. at least one attributable request or registry item supporting fit;
3. the candidate's registry and capability version;
4. the raw fit and its feature/extractor version;
5. the calibrator and threshold version if probability language is used;
6. rejected alternatives or a documented exhaustive single-candidate registry;
7. a final decision type and reason codes; and
8. a linkable delegation contract before execution.

An abstention, clarification, or escalation is sufficient when its reason code resolves to recorded evidence or a policy result and no unauthorized agent was selected.

## Human audit sample

For a stratified sample, two reviewers independently answer:

- Does each source support the claim recorded from it?
- Is the trust tier accurate?
- Was freshness evaluated correctly?
- Would the stored evidence allow the route to be reproduced?
- Is material contrary evidence missing?
- Does the rendered explanation agree with the structured record?

Report agreement and adjudicate disagreements. Automated completeness should never be presented as semantic truth verification.
