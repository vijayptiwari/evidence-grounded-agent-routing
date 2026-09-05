# Reference implementation

This repository now contains an executable research scaffold for the architecture proposed in the white paper. The core uses only the Python standard library; LangGraph and Langfuse are optional integrations.

## What is implemented

- versioned agent and capability registry;
- candidate retrieval with separately measurable recall at `k`;
- typed request, registry, empirical, operational, and policy evidence;
- deterministic policy and availability gates outside the scorer;
- explicit target handling that cannot bypass policy;
- raw-fit scoring kept separate from calibrated probability;
- explicit calibration target/cohort and cost unit/model provenance;
- dependency-free Platt calibration fitted on a distinct calibration split;
- `select`, `parallel`, `clarify`, `abstain`, and `escalate` outcomes;
- schema-compatible Routing Decision Records;
- bounded delegation contracts and separately appended outcome events;
- append-only JSONL storage with a SHA-256 hash chain;
- exact replay and version-drift reporting;
- automated evidence-attribution and minimum-sufficiency checks;
- candidate recall, route accuracy, set-F1, calibration, risk-coverage, constraint, and latency metrics;
- keyword, similarity, and corrected fixed-weight baselines;
- an external-prediction contract for pinned LLM and learned-router baselines;
- capability, alias, empirical, policy, and operational ablations;
- LangGraph `StateGraph`/`Send` adapter; and
- privacy-minimized Langfuse v4 candidate observations.

## Quick start

The package requires Python 3.11 or newer. The router itself has no third-party core dependencies; the repository verification extra adds build and JSON Schema tooling.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts\verify.py
.\.venv\Scripts\egr.exe benchmark --output benchmark/results/latest.json
.\.venv\Scripts\egr.exe route "Why was my subscription charge higher?" --synthetic
.\.venv\Scripts\egr.exe replay-demo "Track my parcel"
```

On Bash-compatible shells:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python scripts/verify.py
egr benchmark --output benchmark/results/latest.json
```

The command-line package contains the synthetic registry and benchmark cases used by these demonstrations. A custom deployment should pass its own versioned paths through `--registry` and, for a benchmark, `--cases`.

Optional integrations:

```bash
pip install -e ".[langgraph,langfuse]"
```

The adapters were executed locally against LangGraph 1.2.11 and Langfuse 4.15.1 on the research cutoff date. [`requirements-optional-tested.txt`](requirements-optional-tested.txt) records those exact versions; the optional CI job retests these pinned compatibility points on every change. The wider optional-dependency ranges express intended compatibility, not proof that every included version combination has been exercised.

LangGraph usage:

```python
from egr import EvidenceGroundedRouter
from egr.integrations.langgraph import build_routing_graph
from egr.registry import AgentRegistry

registry = AgentRegistry.from_path("configs/agents.json")
router = EvidenceGroundedRouter(registry)
graph = build_routing_graph(router)
```

Langfuse usage:

```python
from egr.integrations.langfuse import trace_route

result = trace_route(router, request)
```

The Langfuse adapter sends request identifiers and content references, not raw request text. Configure the SDK with the official Langfuse environment variables.

To add an LLM or learned-router baseline without coupling the benchmark to a provider SDK, generate JSONL using [`benchmark/prompts/llm-classifier.md`](benchmark/prompts/llm-classifier.md) and pass it with `--external NAME=PATH`.

## Repository layout

```text
src/egr/                     routing, policy, calibration, records, replay
src/egr/integrations/        optional LangGraph and Langfuse adapters
src/egr/data/                bundled synthetic CLI registry and cases
configs/agents.json          synthetic versioned agent registry
benchmark/cases.jsonl        calibration and smoke-evaluation cases
benchmark/DATASET_CARD.md    uses, label policy, and contamination disclosure
benchmark/results/           machine-readable generated results
experiments/                 RCA protocol and evidence-quality rubric
schemas/                     decision, contract, outcome, and envelope schemas
examples/                    linked lifecycle examples
tests/                       offline unit and integration tests
scripts/verify.py             cross-platform reproducibility and release checks
```

The verifier confirms that the readable registry and benchmark files remain semantically identical to their bundled CLI copies.

## Calibration boundary

The calibrator is trained only on cases labeled `calibration`. The remaining synthetic cases exercise the evaluation pipeline. However, the dataset and implementation were developed together, so the so-called test cases are **not an independent held-out scientific test**. Their results are software smoke-test results only.

The calibration target is candidate membership in `acceptable_agents`; a production target should instead be a carefully defined downstream success event. Calibration must be repeated by task family and after material model, prompt, registry, policy, tool, or population changes.

The reference ranker does not optimize cost or latency. Those estimates are recorded for later utility experiments, but the current selection reason is `ELIGIBLE_HIGHEST_DECISION_SCORE`, not “best utility.”

## Integrity boundary

`HashChainRecordStore` calculates a canonical payload digest and chains each envelope to the prior envelope. Tests demonstrate that modification is detected. This is not equivalent to digital signing, a trusted timestamp, write-once storage, or an external transparency log.

## Evidence-quality boundary

The automated evaluator confirms attribution fields, freshness flags, eligibility evidence, reason codes, and minimum fit evidence. It cannot prove that a self-asserted capability is true. The human sampling procedure in [`experiments/evidence-rubric.md`](experiments/evidence-rubric.md) evaluates semantic support and missing contrary evidence.

## RCA validation

No debugging-time benefit is claimed. [`experiments/rca-protocol.md`](experiments/rca-protocol.md) defines a randomized crossover study comparing a selected-path trace against the full RDR. This is the required experiment before claiming that the framework improves root-cause analysis.

## Next empirical milestone

Replace or supplement the synthetic cases with independently collected, privacy-reviewed requests. Freeze the implementation before labeling the final evaluation set. Add an LLM classifier baseline and a learned router using a declared model snapshot, then preregister thresholds, primary metrics, and exclusion rules.
