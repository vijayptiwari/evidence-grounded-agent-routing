# Synthetic routing benchmark

This dataset is a **smoke-test benchmark**, not evidence of production effectiveness.

It contains 42 synthetic requests split into 12 calibration and 30 test cases. The cases cover single intent, direct agent requests, multi-intent routing, ambiguity, out-of-domain input, policy review, unavailable agents, missing tools, and prompt-injection-style instructions.

The `acceptable_agents` and `expected_decision` fields are evaluation labels. They are never provided to the router. Only `text` and `context` are router inputs.

Real validation requires independently sampled requests, domain-expert labels, subgroup analysis, versioned production-like registries and policies, and downstream acceptance outcomes.
