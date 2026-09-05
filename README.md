# Evidence-Grounded Agent Routing

A research-backed design for auditable routing and delegation in LangGraph/LangChain-style agentic systems.

By [Vijay Prakash Tiwari](https://github.com/vijayptiwari) · Version 0.1.0

The project replaces an opaque “pick an agent” result with a versioned **Routing Decision Record** that preserves:

- source-linked evidence for every shortlisted candidate;
- capability, policy, authority, and availability eligibility;
- raw fit and calibrated success probability as different fields;
- rejected alternatives and machine-readable reason codes;
- explicit `select`, `parallel`, `clarify`, `abstain`, and `escalate` outcomes;
- a link from the route to a bounded delegation contract; and
- a later outcome event for evaluation, drift monitoring, and root-cause analysis.

## Start here

- [Read the white paper](WHITEPAPER.md)
- [Run the reference implementation](IMPLEMENTATION.md)
- [Check the public claim ledger](CLAIMS.md)
- [Inspect the JSON Schema](schemas/routing-decision.schema.json)
- [See an illustrative decision record](examples/routing-decision.example.json)
- [Review the synthetic benchmark results](benchmark/RESULTS.md)
- [Inspect the RCA study protocol](experiments/rca-protocol.md)
- [Use the portfolio copy](PORTFOLIO_ENTRY.md)
- [Review the release checklist](RELEASE_CHECKLIST.md)

## Why “evidence-grounded”?

This release includes development smoke tests, not independent empirical validation. Calling the framework *evidence-grounded* accurately describes its decision structure; *evidence-based* should be reserved for a later release that reports reproducible results on independently collected data.

## The central design rule

> Evidence is not eligibility. A score is not a probability. Probability is not utility. Policy is not intent. Explanation is not provenance.

The original idea used direct, lexical, semantic, and domain scores in a weighted average. The paper shows why those signals should not be treated as interchangeable and replaces universal weights with source-linked evidence, hard eligibility gates, held-out calibration, and selective outcomes.

## Status

Version 0.1 now includes a dependency-free Python reference implementation, optional LangGraph and Langfuse adapters, a synthetic smoke benchmark, three baselines, calibration and selective-risk metrics, ablations, hash-chained records, replay, schemas, tests, and a preregistration-ready RCA protocol.

The included results are not independent empirical validation. The next milestone is a frozen implementation evaluated on independently collected and labeled requests, with an LLM classifier and learned-router baseline added under pinned model versions.

## What has been physically verified

- the dependency-free route, policy, record, contract, outcome, replay, integrity, and benchmark paths;
- single-agent and parallel `Send` execution through LangGraph 1.2.11;
- privacy-minimized observations through the Langfuse 4.15.1 client with export disabled;
- five JSON Schemas and their examples under Draft 2020-12;
- a wheel and source distribution accepted by `twine check`; and
- 16 automated tests, including detection of record tampering and version drift.

These are implementation checks in the reference environment, not evidence of production effectiveness or general security.

## Run it

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts\verify.py
.\.venv\Scripts\egr.exe replay-demo "Track my parcel"
```

On Bash-compatible shells, activate the environment and use the same `python scripts/verify.py` command. The CLI bundles the synthetic registry and benchmark cases, so `egr route`, `egr benchmark`, and `egr replay-demo` work outside the checkout unless custom `--registry` or `--cases` paths are supplied.

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for focused commands, optional LangGraph/Langfuse installation, and external LLM-baseline instructions.

## Publication checklist

Before making the repository public:

- add the author's preferred name and contact or profile link;
- choose a software/content license deliberately;
- set the final GitHub repository URL in package, citation, and portfolio metadata;
- enable private vulnerability reporting and branch protection;
- tag the reviewed release, for example `v0.1.0`; and
- archive a release copy with a DOI service such as Zenodo if formal citation is desired.

The complete, auditable sequence is in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md). `python scripts/verify.py --release` intentionally fails while public identity, license, citation, or repository metadata is unresolved.

## Suggested citation

```text
Vijay Prakash Tiwari. “Evidence-Grounded Agent Routing: A Decision-Provenance
Framework for Auditable Routing and Delegation in Agentic Systems.” Version
0.1.0, 2026. https://github.com/vijayptiwari/evidence-grounded-agent-routing
```

Machine-readable citation metadata is available in [CITATION.cff](CITATION.cff). Add the version DOI after the first archival release.

## Important boundary

This work provides an engineering architecture, reference implementation, schemas, and evaluation protocol. It does not claim legal compliance, guaranteed safety, or measured production improvement.

## License

Software and machine-executable project materials are licensed under Apache-2.0. The white paper, documentation, benchmark and research artifacts are licensed under CC BY 4.0. See [LICENSE.md](LICENSE.md) for the exact scope and full license texts.

## Contributing, support, and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for evidence and test requirements, [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for participation standards, [GOVERNANCE.md](GOVERNANCE.md) for change and claim governance, [SUPPORT.md](SUPPORT.md) for the support boundary, and [SECURITY.md](SECURITY.md) for private reporting guidance and security limitations.
