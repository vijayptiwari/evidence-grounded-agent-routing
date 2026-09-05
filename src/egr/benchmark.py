from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import time
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Protocol

from .calibration import PlattCalibrator
from .models import DecisionOutcome, RoutingRequest
from .policy import DeterministicPolicyEngine
from .quality import evaluate_evidence_quality
from .registry import AgentRegistry, CandidateRetriever, normalize, phrase_similarity
from .router import EvidenceGroundedRouter, RouterConfig


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    case_id: str
    split: str
    text: str
    acceptable_agents: frozenset[str]
    expected_decision: str
    context: dict[str, Any]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BenchmarkCase":
        return cls(
            case_id=value["case_id"],
            split=value["split"],
            text=value["text"],
            acceptable_agents=frozenset(value["acceptable_agents"]),
            expected_decision=value["expected_decision"],
            context=value.get("context", {}),
        )

    def request(self) -> RoutingRequest:
        return RoutingRequest(
            request_id=self.case_id,
            text=self.text,
            explicit_agent_id=self.context.get("explicit_agent_id"),
            blocked_agent_ids=frozenset(self.context.get("blocked_agent_ids", [])),
            unavailable_agent_ids=frozenset(self.context.get("unavailable_agent_ids", [])),
            required_tools=frozenset(self.context.get("required_tools", [])),
            review_required=bool(self.context.get("review_required", False)),
            allow_parallel=bool(self.context.get("allow_parallel", True)),
            metadata={"synthetic": True, "environment": "test", "context_version": "benchmark@1.0.0"},
        )


@dataclass(frozen=True, slots=True)
class Prediction:
    decision: str
    selected_agents: tuple[str, ...]
    ranked_candidates: tuple[str, ...]
    probabilities: dict[str, float]
    record: dict[str, Any] | None = None
    latency_ms: float = 0.0


class Predictor(Protocol):
    def predict(self, case: BenchmarkCase) -> Prediction: ...


def load_cases(path: str | Path) -> tuple[BenchmarkCase, ...]:
    return tuple(
        BenchmarkCase.from_dict(json.loads(line))
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


class KeywordBaseline:
    name = "keyword-baseline"

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def predict(self, case: BenchmarkCase) -> Prediction:
        started = time.perf_counter()
        request = case.request()
        explicit = self.registry.detect_explicit_agent(request)
        if explicit:
            registered = self.registry.get(explicit)
            decision = "select" if registered else "clarify"
            selected = (explicit,) if registered else ()
            ranked = (explicit,) if registered else ()
        else:
            scores: list[tuple[str, float]] = []
            normalized_text = normalize(case.text)
            for agent in self.registry.agents:
                keywords = [keyword for capability in agent.capabilities for keyword in capability.keywords]
                score = sum(1.0 for keyword in keywords if normalize(keyword) in normalized_text)
                scores.append((agent.agent_id, score))
            scores.sort(key=lambda item: (-item[1], item[0]))
            ranked = tuple(agent_id for agent_id, _ in scores[:5])
            if scores[0][1] == 0:
                decision, selected = "abstain", ()
            else:
                decision, selected = "select", (scores[0][0],)
        return Prediction(decision, selected, ranked, {}, latency_ms=(time.perf_counter() - started) * 1000)


class SimilarityBaseline:
    name = "similarity-top1-baseline"

    def __init__(self, registry: AgentRegistry, top_k: int = 5):
        self.registry = registry
        self.retriever = CandidateRetriever(top_k=top_k)

    def predict(self, case: BenchmarkCase) -> Prediction:
        started = time.perf_counter()
        request = case.request()
        explicit = self.registry.detect_explicit_agent(request)
        candidates = self.retriever.retrieve(request, self.registry, explicit)
        ranked = tuple(item.agent.agent_id for item in candidates)
        if explicit and not self.registry.get(explicit):
            decision, selected = "clarify", ()
        elif candidates and candidates[0].score >= 0.3:
            decision, selected = "select", (candidates[0].agent.agent_id,)
        else:
            decision, selected = "abstain", ()
        return Prediction(decision, selected, ranked, {}, latency_ms=(time.perf_counter() - started) * 1000)


class ScoreOnlyBaseline:
    """The original 20/30/40/10 proposal, with corrected arithmetic."""

    name = "fixed-weight-score-only"

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.policy = DeterministicPolicyEngine()

    def predict(self, case: BenchmarkCase) -> Prediction:
        started = time.perf_counter()
        request = case.request()
        explicit = self.registry.detect_explicit_agent(request)
        scored: list[tuple[str, float]] = []
        for agent in self.registry.agents:
            if self.policy.evaluate(request, agent).eligibility.value != "eligible":
                continue
            direct = 10.0 if explicit == agent.agent_id else 0.0
            alias = 10.0 * max((phrase_similarity(case.text, name) for name in agent.aliases), default=0.0)
            semantic = 10.0 * max(
                (
                    phrase_similarity(case.text, phrase)
                    for capability in agent.capabilities
                    for phrase in (capability.description, *capability.keywords)
                ),
                default=0.0,
            )
            domain = 10.0 * max((phrase_similarity(case.text, domain) for domain in agent.domains), default=0.0)
            intent_score = 0.2 * direct + 0.3 * alias + 0.4 * semantic + 0.1 * domain
            scored.append((agent.agent_id, intent_score))
        scored.sort(key=lambda item: (-item[1], item[0]))
        ranked = tuple(agent_id for agent_id, _ in scored[:5])
        if scored and scored[0][1] > 0:
            decision, selected = "select", (scored[0][0],)
        else:
            decision, selected = "abstain", ()
        return Prediction(decision, selected, ranked, {}, latency_ms=(time.perf_counter() - started) * 1000)


class EvidencePredictor:
    name = "evidence-grounded"

    def __init__(self, router: EvidenceGroundedRouter):
        self.router = router

    def predict(self, case: BenchmarkCase) -> Prediction:
        started = time.perf_counter()
        result = self.router.route(
            case.request(),
            decision_id=f"rdr_{case.case_id}",
            created_at="2026-09-05T00:00:00Z",
        )
        probabilities = {
            candidate.agent_id: candidate.calibrated_success_probability
            for candidate in result.candidates
            if candidate.calibrated_success_probability is not None
        }
        ranked = tuple(
            candidate.agent_id
            for candidate in sorted(
                result.candidates,
                key=lambda item: (-(item.calibrated_success_probability if item.calibrated_success_probability is not None else item.raw_fit or 0.0), item.agent_id),
            )
        )
        return Prediction(
            decision=result.outcome.value,
            selected_agents=result.selected_agent_ids,
            ranked_candidates=ranked,
            probabilities=probabilities,
            record=result.record,
            latency_ms=(time.perf_counter() - started) * 1000,
        )


class ExternalPredictionBaseline:
    """Evaluate pinned predictions produced by an LLM or learned router elsewhere."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.predictions = {
            item["case_id"]: item
            for item in (
                json.loads(line)
                for line in self.path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        }

    def predict(self, case: BenchmarkCase) -> Prediction:
        started = time.perf_counter()
        if case.case_id not in self.predictions:
            raise ValueError(f"External prediction file has no row for {case.case_id}")
        value = self.predictions[case.case_id]
        return Prediction(
            decision=value["decision"],
            selected_agents=tuple(value.get("selected_agents", [])),
            ranked_candidates=tuple(value.get("ranked_candidates", [])),
            probabilities={key: float(score) for key, score in value.get("probabilities", {}).items()},
            latency_ms=(time.perf_counter() - started) * 1000,
        )


def choose_threshold(observations: Iterable[tuple[float, int]], calibrator: PlattCalibrator) -> float:
    values = [(calibrator.predict(score), label) for score, label in observations]
    best_threshold = 0.5
    best_score = -1.0
    for step in range(10, 91):
        threshold = step / 100
        true_positive = true_negative = false_positive = false_negative = 0
        for probability, label in values:
            predicted = int(probability >= threshold)
            true_positive += int(predicted == 1 and label == 1)
            true_negative += int(predicted == 0 and label == 0)
            false_positive += int(predicted == 1 and label == 0)
            false_negative += int(predicted == 0 and label == 1)
        sensitivity = true_positive / max(1, true_positive + false_negative)
        specificity = true_negative / max(1, true_negative + false_positive)
        balanced_accuracy = (sensitivity + specificity) / 2
        if balanced_accuracy > best_score:
            best_score = balanced_accuracy
            best_threshold = threshold
    return best_threshold


def fit_evidence_router(
    registry: AgentRegistry,
    calibration_cases: tuple[BenchmarkCase, ...],
    config: RouterConfig,
) -> EvidenceGroundedRouter:
    uncalibrated = EvidenceGroundedRouter(registry, config=config)
    observations = uncalibrated.raw_candidate_observations(
        (case.request(), set(case.acceptable_agents)) for case in calibration_cases
    )
    calibrator = PlattCalibrator.fit(
        observations,
        target="candidate_in_synthetic_acceptable_agents",
        cohort="synthetic-calibration-split@1.0.0",
    )
    threshold = choose_threshold(observations, calibrator)
    calibrated_config = replace(
        config,
        selection_threshold=threshold,
        parallel_threshold=threshold,
        version=f"{config.version}+threshold-{threshold:.2f}",
    )
    return EvidenceGroundedRouter(registry, config=calibrated_config, calibrator=calibrator)


def _case_correct(case: BenchmarkCase, prediction: Prediction) -> bool:
    if prediction.decision != case.expected_decision:
        return False
    if case.expected_decision in {DecisionOutcome.SELECT.value, DecisionOutcome.PARALLEL.value}:
        return set(prediction.selected_agents) == set(case.acceptable_agents)
    return not prediction.selected_agents


def _set_f1(expected: set[str], actual: set[str]) -> float:
    if not expected and not actual:
        return 1.0
    if not expected or not actual:
        return 0.0
    true_positive = len(expected & actual)
    precision = true_positive / len(actual)
    recall = true_positive / len(expected)
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def _ece(observations: list[tuple[float, int]], bins: int = 10) -> float | None:
    if not observations:
        return None
    total = len(observations)
    error = 0.0
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        bucket = [item for item in observations if lower <= item[0] < upper or (index == bins - 1 and item[0] == 1.0)]
        if not bucket:
            continue
        confidence = sum(probability for probability, _ in bucket) / len(bucket)
        accuracy = sum(label for _, label in bucket) / len(bucket)
        error += len(bucket) / total * abs(confidence - accuracy)
    return error


def _bootstrap_mean_ci(values: list[float | bool], *, seed: int = 20260905, samples: int = 2_000) -> list[float] | None:
    if not values:
        return None
    generator = random.Random(seed)
    numeric = [float(value) for value in values]
    estimates = sorted(
        statistics.fmean(generator.choice(numeric) for _ in numeric) for _ in range(samples)
    )
    lower = estimates[int(0.025 * samples)]
    upper = estimates[min(samples - 1, int(0.975 * samples))]
    return [round(lower, 6), round(upper, 6)]


def _paired_comparison(
    evidence_details: list[dict[str, Any]], baseline_details: list[dict[str, Any]]
) -> dict[str, Any]:
    evidence = {item["case_id"]: bool(item["correct"]) for item in evidence_details}
    baseline = {item["case_id"]: bool(item["correct"]) for item in baseline_details}
    case_ids = sorted(evidence.keys() & baseline.keys())
    differences = [float(evidence[case_id]) - float(baseline[case_id]) for case_id in case_ids]
    evidence_only = sum(evidence[case_id] and not baseline[case_id] for case_id in case_ids)
    baseline_only = sum(baseline[case_id] and not evidence[case_id] for case_id in case_ids)
    discordant = evidence_only + baseline_only
    if discordant:
        tail = sum(
            math.comb(discordant, k) * (0.5 ** discordant)
            for k in range(min(evidence_only, baseline_only) + 1)
        )
        p_value = min(1.0, 2 * tail)
    else:
        p_value = 1.0
    return {
        "paired_route_accuracy_difference": round(statistics.fmean(differences), 6),
        "bootstrap_95ci": _bootstrap_mean_ci(differences),
        "evidence_correct_baseline_wrong": evidence_only,
        "baseline_correct_evidence_wrong": baseline_only,
        "mcnemar_exact_two_sided_p": round(p_value, 6),
        "warning": "Exploratory synthetic-development-set comparison; not confirmatory inference.",
    }


def _constraint_violation(case: BenchmarkCase, prediction: Prediction, registry: AgentRegistry) -> bool:
    blocked = set(case.context.get("blocked_agent_ids", []))
    unavailable = set(case.context.get("unavailable_agent_ids", []))
    required_tools = set(case.context.get("required_tools", []))
    for agent_id in prediction.selected_agents:
        agent = registry.get(agent_id)
        if agent_id in blocked or agent_id in unavailable or agent is None:
            return True
        if required_tools - set(agent.tools):
            return True
        if case.context.get("review_required") or "human-review" in agent.policy_labels:
            return True
    return False


def evaluate_predictor(
    predictor: Predictor,
    cases: tuple[BenchmarkCase, ...],
    registry: AgentRegistry,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    predictions: list[tuple[BenchmarkCase, Prediction]] = [(case, predictor.predict(case)) for case in cases]
    correct = [_case_correct(case, prediction) for case, prediction in predictions]
    autonomous = [item for item in predictions if item[1].decision in {"select", "parallel"}]
    deferred = [item for item in predictions if item[1].decision not in {"select", "parallel"}]
    routeable = [item for item in predictions if item[0].acceptable_agents]
    top1_cases = [item for item in predictions if item[0].expected_decision == "select"]
    probability_observations = [
        (probability, int(agent_id in case.acceptable_agents))
        for case, prediction in predictions
        for agent_id, probability in prediction.probabilities.items()
    ]
    evidence_reports = [
        evaluate_evidence_quality(prediction.record)
        for _, prediction in predictions
        if prediction.record is not None
    ]

    candidate_recall = [
        len(set(prediction.ranked_candidates) & set(case.acceptable_agents)) / len(case.acceptable_agents)
        for case, prediction in routeable
    ]
    top1_accuracy = [
        bool(prediction.selected_agents and prediction.selected_agents[0] in case.acceptable_agents)
        for case, prediction in top1_cases
    ]
    constraint_violations = [
        _constraint_violation(case, prediction, registry) for case, prediction in predictions
    ]
    brier = (
        sum((probability - label) ** 2 for probability, label in probability_observations)
        / len(probability_observations)
        if probability_observations
        else None
    )
    details = [
        {
            "case_id": case.case_id,
            "expected_decision": case.expected_decision,
            "expected_agents": sorted(case.acceptable_agents),
            "actual_decision": prediction.decision,
            "actual_agents": list(prediction.selected_agents),
            "correct": is_correct,
        }
        for (case, prediction), is_correct in zip(predictions, correct, strict=True)
    ]
    metrics = {
        "cases": len(cases),
        "route_accuracy": round(sum(correct) / len(correct), 6),
        "route_accuracy_bootstrap_95ci": _bootstrap_mean_ci(correct),
        "top1_accuracy": round(sum(top1_accuracy) / len(top1_accuracy), 6) if top1_accuracy else None,
        "mean_set_f1": round(
            statistics.fmean(
                _set_f1(set(case.acceptable_agents), set(prediction.selected_agents))
                for case, prediction in predictions
            ),
            6,
        ),
        "candidate_recall_at_k": round(statistics.fmean(candidate_recall), 6) if candidate_recall else None,
        "candidate_k": 5,
        "coverage": round(len(autonomous) / len(predictions), 6),
        "selective_risk": round(
            1 - sum(_case_correct(case, prediction) for case, prediction in autonomous) / len(autonomous),
            6,
        ) if autonomous else None,
        "deferral_precision": round(
            sum(case.expected_decision not in {"select", "parallel"} for case, _ in deferred) / len(deferred),
            6,
        ) if deferred else None,
        "constraint_violation_rate": round(sum(constraint_violations) / len(constraint_violations), 6),
        "brier_score": round(brier, 6) if brier is not None else None,
        "expected_calibration_error": round(_ece(probability_observations), 6) if probability_observations else None,
        "mean_evidence_validity": round(statistics.fmean(item.validity for item in evidence_reports), 6) if evidence_reports else None,
        "mean_evidence_sufficiency": round(statistics.fmean(item.sufficiency for item in evidence_reports), 6) if evidence_reports else None,
        "median_latency_ms": round(statistics.median(prediction.latency_ms for _, prediction in predictions), 6),
    }
    return metrics, details


def run_benchmark(
    registry_path: str | Path,
    cases_path: str | Path,
    external_predictions: dict[str, str | Path] | None = None,
) -> dict[str, Any]:
    registry = AgentRegistry.from_path(registry_path)
    cases = load_cases(cases_path)
    calibration_cases = tuple(case for case in cases if case.split == "calibration")
    test_cases = tuple(case for case in cases if case.split == "test")

    base_config = RouterConfig()
    full_router = fit_evidence_router(registry, calibration_cases, base_config)
    predictors: list[tuple[str, Predictor]] = [
        (KeywordBaseline.name, KeywordBaseline(registry)),
        (SimilarityBaseline.name, SimilarityBaseline(registry)),
        (ScoreOnlyBaseline.name, ScoreOnlyBaseline(registry)),
        (EvidencePredictor.name, EvidencePredictor(full_router)),
    ]
    for name, path in (external_predictions or {}).items():
        predictors.append((name, ExternalPredictionBaseline(path)))
    results: dict[str, Any] = {}
    details: dict[str, Any] = {}
    for name, predictor in predictors:
        results[name], details[name] = evaluate_predictor(predictor, test_cases, registry)

    ablation_configs = {
        "full": base_config,
        "without-capability-evidence": replace(base_config, include_capability=False, version="egr-router@0.1.0-ablate-capability"),
        "without-alias-evidence": replace(base_config, include_alias=False, version="egr-router@0.1.0-ablate-alias"),
        "without-empirical-evidence": replace(base_config, include_empirical=False, version="egr-router@0.1.0-ablate-empirical"),
        "without-policy-gate": replace(base_config, enforce_policy=False, version="egr-router@0.1.0-ablate-policy"),
        "without-operational-gate": replace(base_config, enforce_operational=False, version="egr-router@0.1.0-ablate-operational"),
    }
    ablations: dict[str, Any] = {}
    for name, config in ablation_configs.items():
        router = fit_evidence_router(registry, calibration_cases, config)
        metrics, _ = evaluate_predictor(EvidencePredictor(router), test_cases, registry)
        ablations[name] = {
            "metrics": metrics,
            "calibrator": router.calibrator.to_dict() if router.calibrator else None,
            "selection_threshold": router.config.selection_threshold,
        }

    evidence_details = details[EvidencePredictor.name]
    comparisons = {
        name: _paired_comparison(evidence_details, baseline_details)
        for name, baseline_details in details.items()
        if name != EvidencePredictor.name
    }
    risk_coverage_curve: list[dict[str, Any]] = []
    for threshold in (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90):
        threshold_router = EvidenceGroundedRouter(
            registry,
            config=replace(
                full_router.config,
                selection_threshold=threshold,
                parallel_threshold=threshold,
                version=f"{base_config.version}+curve-{threshold:.2f}",
            ),
            calibrator=full_router.calibrator,
        )
        curve_metrics, _ = evaluate_predictor(EvidencePredictor(threshold_router), test_cases, registry)
        risk_coverage_curve.append(
            {
                "threshold": threshold,
                "coverage": curve_metrics["coverage"],
                "selective_risk": curve_metrics["selective_risk"],
                "route_accuracy": curve_metrics["route_accuracy"],
            }
        )

    registry_bytes = Path(registry_path).read_bytes()
    cases_bytes = Path(cases_path).read_bytes()

    return {
        "benchmark_version": "synthetic-routing-benchmark@1.0.0",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "research_boundary": "Synthetic smoke-test results; not evidence of production effectiveness.",
        "registry_version": registry.version,
        "registry_sha256": hashlib.sha256(registry_bytes).hexdigest(),
        "cases_sha256": hashlib.sha256(cases_bytes).hexdigest(),
        "calibration_cases": len(calibration_cases),
        "test_cases": len(test_cases),
        "full_calibrator": full_router.calibrator.to_dict() if full_router.calibrator else None,
        "full_selection_threshold": full_router.config.selection_threshold,
        "results": results,
        "ablations": ablations,
        "paired_comparisons": comparisons,
        "risk_coverage_curve": risk_coverage_curve,
        "case_results": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the evidence-grounded routing benchmark")
    parser.add_argument("--registry", default="configs/agents.json")
    parser.add_argument("--cases", default="benchmark/cases.jsonl")
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--external",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Add pinned JSONL predictions from an external LLM or learned router",
    )
    args = parser.parse_args(argv)
    external = dict(item.split("=", 1) for item in args.external)
    report = run_benchmark(args.registry, args.cases, external)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote benchmark report to {output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
