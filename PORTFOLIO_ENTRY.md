# Portfolio copy

Publication-ready copy for the version 0.1.0 repository release.

## Project title

Evidence-Grounded Agent Routing

## One-line description

Designed a decision-provenance framework that makes multi-agent routing inspectable, policy-aware, uncertainty-aware, and empirically testable.

## Short portfolio description

I developed a research-backed architecture and executable Python reference implementation for routing and delegation in LangGraph/LangChain-style agentic systems. Instead of storing only the selected agent or an uncalibrated score, the framework records source-linked evidence, versioned capability claims, policy eligibility, uncertainty, rejected alternatives, and downstream outcomes. The project includes a detailed white paper, optional LangGraph and Langfuse adapters, machine-readable lifecycle schemas, replay and integrity checks, a synthetic benchmark, baselines, calibration, risk-coverage metrics, ablations, tests, and an RCA experiment protocol.

## Resume bullet

- Authored an evidence-grounded agent-routing framework and JSON Schema that separates capability evidence, policy eligibility, calibrated uncertainty, and business utility, with explicit abstention, escalation, provenance, and evaluation controls.
- Built and physically verified a dependency-free Python prototype with LangGraph/Langfuse adapters, deterministic replay, tamper detection, lifecycle schemas, synthetic baselines and ablations, and a cross-platform release gate.

## Case-study summary

**Problem:** Prompt-based routers often produce only an agent label, making failures difficult to reproduce, audit, or diagnose.

**Insight:** Adding more scores does not solve the problem if the scores lack source provenance, calibration, versioning, and non-selection outcomes.

**Solution:** A two-plane architecture: an immutable decision record for retrieval, evidence, eligibility, ranking, and uncertainty; followed by a bounded delegation contract and a separately recorded execution outcome.

**Research basis:** Synthesized peer-reviewed work on task allocation, LLM routing, selective prediction, calibration, provenance, and explainability with current LangGraph, LangChain, Langfuse, OpenTelemetry, A2A, and NIST documentation.

**Deliverables:** White paper, executable routing package, LangGraph/Langfuse adapters, lifecycle schemas, hash-chained storage, exact replay, worked records, benchmark harness, baselines, calibration, ablations, tests, security analysis, and a falsifiable RCA protocol.

**Verification:** Sixteen automated tests exercise the core lifecycle plus real LangGraph 1.2.11 and Langfuse 4.15.1 integration paths. Five schemas and examples validate under JSON Schema Draft 2020-12. The built wheel routes and regenerates the bundled 42-case benchmark outside the source checkout.

**Status:** Reference implementation and synthetic smoke benchmark complete; independently collected empirical validation remains the next phase. The authored development set demonstrates executable behavior and catches meaningful ablation failures, but it supports no production-accuracy or compliance claim.

## Suggested launch post

I’ve published *Evidence-Grounded Agent Routing*, a design proposal for making agent selection auditable in production.

The core idea is simple: a router should not return only an agent name—or hide several unrelated signals inside one confidence score. It should preserve the evidence considered, capability and policy eligibility, rejected alternatives, configuration versions, uncertainty, and the eventual execution outcome.

The paper proposes a Routing Decision Record, explicit clarification/abstention/escalation paths, a bounded delegation contract, and an evaluation plan for accuracy, candidate recall, calibration, risk coverage, policy violations, cost, latency, and RCA time.

The design is implemented and physically tested, including single and parallel LangGraph dispatch, privacy-minimized Langfuse observations, exact replay, tamper detection, schemas, packaging, and a synthetic benchmark. This first release is still intentionally called *evidence-grounded*: those checks establish a working prototype, not independent empirical validation.

Read it here: https://github.com/vijayptiwari/evidence-grounded-agent-routing

#AgenticAI #LangGraph #LangChain #LLMOps #AIEngineering #ResponsibleAI

## Interview talking points

- Why an explanation string is not the same as decision provenance.
- Why direct user intent is a control signal and policy is an eligibility gate—not just another feature weight.
- Why raw LLM scores must not be called probabilities without held-out calibration.
- Why candidate recall must be measured separately from final agent selection.
- How clarification, abstention, and escalation prevent forced routing.
- How the RDR maps to LangGraph state and Langfuse observations without capturing hidden chain-of-thought.
- Which hypotheses still need experiments and what would falsify them.
