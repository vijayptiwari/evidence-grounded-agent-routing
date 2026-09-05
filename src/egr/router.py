from __future__ import annotations

import hashlib
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from .calibration import PlattCalibrator
from .models import (
    AgentSpec,
    CandidateEvaluation,
    DecisionOutcome,
    Eligibility,
    EvidenceItem,
    RouteResult,
    RoutingRequest,
)
from .policy import DeterministicPolicyEngine, PolicyEvaluation
from .registry import AgentRegistry, CandidateRetriever, RetrievedCandidate, normalize, phrase_similarity


@dataclass(frozen=True, slots=True)
class RouterConfig:
    version: str = "egr-router@0.1.0"
    feature_version: str = "evidence-features@0.1.0"
    schema_version: str = "1.0.0"
    selection_threshold: float = 0.55
    clarification_floor: float = 0.25
    margin_threshold: float = 0.12
    parallel_threshold: float = 0.45
    min_empirical_samples: int = 20
    capability_weight: float = 0.72
    alias_weight: float = 0.13
    empirical_weight: float = 0.15
    include_capability: bool = True
    include_alias: bool = True
    include_empirical: bool = True
    enforce_policy: bool = True
    enforce_operational: bool = True

    def __post_init__(self) -> None:
        for name in ("selection_threshold", "clarification_floor", "margin_threshold", "parallel_threshold"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between zero and one")


class EvidenceGroundedRouter:
    def __init__(
        self,
        registry: AgentRegistry,
        *,
        config: RouterConfig | None = None,
        policy_engine: DeterministicPolicyEngine | None = None,
        retriever: CandidateRetriever | None = None,
        calibrator: PlattCalibrator | None = None,
    ):
        self.registry = registry
        self.config = config or RouterConfig()
        self.policy_engine = policy_engine or DeterministicPolicyEngine()
        self.retriever = retriever or CandidateRetriever()
        self.calibrator = calibrator

    @staticmethod
    def _uncertainty(probability: float) -> float:
        if probability <= 0.0 or probability >= 1.0:
            return 0.0
        entropy = -(probability * math.log2(probability) + (1 - probability) * math.log2(1 - probability))
        return round(entropy, 6)

    @staticmethod
    def _best_alias_score(text: str, agent: AgentSpec) -> float:
        return max((phrase_similarity(text, alias) for alias in agent.aliases), default=0.0)

    @staticmethod
    def _capability_scores(text: str, agent: AgentSpec) -> dict[str, float]:
        values: dict[str, float] = {}
        for capability in agent.capabilities:
            phrases = (capability.description, *capability.keywords)
            values[capability.capability_id] = round(
                max((phrase_similarity(text, phrase) for phrase in phrases), default=0.0),
                6,
            )
        return values

    def _policy(self, request: RoutingRequest, agent: AgentSpec) -> PolicyEvaluation:
        if self.config.enforce_policy:
            if self.config.enforce_operational:
                return self.policy_engine.evaluate(request, agent)
            request = RoutingRequest(
                request_id=request.request_id,
                text=request.text,
                locale=request.locale,
                content_ref=request.content_ref,
                explicit_agent_id=request.explicit_agent_id,
                blocked_agent_ids=request.blocked_agent_ids,
                unavailable_agent_ids=frozenset(),
                required_tools=frozenset(),
                review_required=request.review_required,
                allow_parallel=request.allow_parallel,
                metadata=request.metadata,
            )
            return self.policy_engine.evaluate(request, agent)
        return PolicyEvaluation(Eligibility.ELIGIBLE, ("POLICY_NOT_ENFORCED",), "ablation")

    def _evaluate_candidate(
        self,
        request: RoutingRequest,
        retrieved: RetrievedCandidate,
        explicit_agent_id: str | None,
        observed_at: str,
    ) -> CandidateEvaluation:
        agent = retrieved.agent
        policy = self._policy(request, agent)
        capability_scores = self._capability_scores(request.text, agent)
        capability_score = max(capability_scores.values(), default=0.0) if self.config.include_capability else 0.0
        alias_score = self._best_alias_score(request.text, agent) if self.config.include_alias else 0.0
        empirical_available = (
            self.config.include_empirical
            and agent.empirical_success_rate is not None
            and agent.empirical_sample_size >= self.config.min_empirical_samples
        )
        empirical_score = float(agent.empirical_success_rate) if empirical_available else 0.0

        evidence: list[EvidenceItem] = []
        reason_codes = list(policy.reason_codes)

        if explicit_agent_id == agent.agent_id:
            evidence.append(
                EvidenceItem(
                    evidence_id=f"ev-{request.request_id}-{agent.agent_id}-explicit",
                    family="request",
                    source_type="observed",
                    source_ref=request.content_ref or f"memory://requests/{request.request_id}",
                    source_version=hashlib.sha256(request.text.encode("utf-8")).hexdigest()[:12],
                    method="explicit-agent-parser@0.1.0",
                    observed_at=observed_at,
                    trust_tier="verified_source",
                    freshness="current",
                    query_span=agent.agent_id,
                    capability_id=None,
                    raw_value=True,
                )
            )
            reason_codes.append("EXPLICIT_ELIGIBLE_TARGET" if policy.eligibility == Eligibility.ELIGIBLE else "EXPLICIT_TARGET_BLOCKED")

        if self.config.include_alias and alias_score > 0:
            evidence.append(
                EvidenceItem(
                    evidence_id=f"ev-{request.request_id}-{agent.agent_id}-alias",
                    family="request",
                    source_type="observed",
                    source_ref=request.content_ref or f"memory://requests/{request.request_id}",
                    source_version=hashlib.sha256(request.text.encode("utf-8")).hexdigest()[:12],
                    method=self.config.feature_version,
                    observed_at=observed_at,
                    trust_tier="verified_source",
                    freshness="current",
                    query_span=None,
                    capability_id=None,
                    raw_value={"relation": "alias_match", "score": alias_score},
                )
            )
            if alias_score >= 0.5:
                reason_codes.append("LEXICAL_MATCH")

        for capability_id, score in capability_scores.items():
            if self.config.include_capability and score > 0:
                evidence.append(
                    EvidenceItem(
                        evidence_id=f"ev-{request.request_id}-{agent.agent_id}-{capability_id}",
                        family="registry",
                        source_type="asserted",
                        source_ref=f"registry://{self.registry.version}/{agent.agent_id}/{capability_id}",
                        source_version=self.registry.version,
                        method=self.config.feature_version,
                        observed_at=observed_at,
                        trust_tier="self_asserted",
                        freshness="current",
                        query_span=None,
                        capability_id=capability_id,
                        raw_value={"relation": "capability_match", "score": score},
                    )
                )
        if capability_score >= 0.5:
            reason_codes.append("CAPABILITY_MATCH")
        elif capability_score > 0:
            reason_codes.append("WEAK_CAPABILITY_MATCH")

        if empirical_available:
            evidence.append(
                EvidenceItem(
                    evidence_id=f"ev-{request.request_id}-{agent.agent_id}-empirical",
                    family="empirical",
                    source_type=agent.empirical_source_type,
                    source_ref=agent.empirical_source_ref or f"registry://{self.registry.version}/{agent.agent_id}/performance",
                    source_version=agent.empirical_window or "unknown",
                    method=agent.empirical_method,
                    observed_at=observed_at,
                    trust_tier=agent.empirical_trust_tier,
                    freshness=agent.empirical_freshness,
                    query_span=None,
                    capability_id=None,
                    raw_value={
                        "success_rate": empirical_score,
                        "sample_size": agent.empirical_sample_size,
                        "outcome_definition": agent.empirical_outcome_definition,
                    },
                )
            )

        context_version = request.metadata.get("context_version")
        if context_version:
            evidence.append(
                EvidenceItem(
                    evidence_id=f"ev-{request.request_id}-{agent.agent_id}-context",
                    family="context",
                    source_type="retrieved",
                    source_ref=f"context://{context_version}",
                    source_version=context_version,
                    method="context-snapshot-lookup",
                    observed_at=observed_at,
                    trust_tier="verified_source",
                    freshness="current",
                    query_span=None,
                    capability_id=None,
                    raw_value={"snapshot_present": True},
                )
            )

        if request.unavailable_agent_ids or request.required_tools:
            missing_tools = sorted(request.required_tools - set(agent.tools))
            evidence.append(
                EvidenceItem(
                    evidence_id=f"ev-{request.request_id}-{agent.agent_id}-operational",
                    family="operational",
                    source_type="observed",
                    source_ref=f"context://{context_version or 'unversioned'}/operational/{agent.agent_id}",
                    source_version=context_version or "context@unversioned",
                    method="operational-eligibility-check",
                    observed_at=observed_at,
                    trust_tier="verified_source",
                    freshness="current",
                    query_span=None,
                    capability_id=None,
                    raw_value={
                        "available": agent.agent_id not in request.unavailable_agent_ids,
                        "required_tools": sorted(request.required_tools),
                        "missing_tools": missing_tools,
                    },
                )
            )

        evidence.append(
            EvidenceItem(
                evidence_id=f"ev-{request.request_id}-{agent.agent_id}-policy",
                family="policy",
                source_type="policy",
                source_ref=f"policy://{self.policy_engine.version}/{policy.rule_id}",
                source_version=self.policy_engine.version,
                method="deterministic-policy-evaluation",
                observed_at=observed_at,
                trust_tier="verified_source",
                freshness="current",
                query_span=None,
                capability_id=None,
                raw_value=policy.eligibility.value,
            )
        )

        components: list[tuple[float, float]] = []
        if self.config.include_capability:
            components.append((self.config.capability_weight, capability_score))
        if self.config.include_alias:
            components.append((self.config.alias_weight, alias_score))
        if empirical_available:
            components.append((self.config.empirical_weight, empirical_score))
        denominator = sum(weight for weight, _ in components) or 1.0
        raw_fit = round(sum(weight * value for weight, value in components) / denominator, 6)
        probability = self.calibrator.predict(raw_fit) if self.calibrator else None
        uncertainty = self._uncertainty(probability) if probability is not None else None

        return CandidateEvaluation(
            agent_id=agent.agent_id,
            agent_version=agent.version,
            retrieval_rank=retrieved.rank,
            retrieval_score=retrieved.score,
            eligibility=policy.eligibility,
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            evidence=tuple(evidence),
            raw_fit=raw_fit,
            calibrated_success_probability=round(probability, 6) if probability is not None else None,
            uncertainty=uncertainty,
            expected_cost=agent.expected_cost,
            expected_latency_ms=agent.expected_latency_ms,
            capability_scores=capability_scores,
        )

    @staticmethod
    def _decision_score(candidate: CandidateEvaluation) -> float:
        if candidate.calibrated_success_probability is not None:
            return candidate.calibrated_success_probability
        return candidate.raw_fit or 0.0

    def _parallel_selection(self, request: RoutingRequest, eligible: list[CandidateEvaluation]) -> tuple[str, ...]:
        if not request.allow_parallel or " and " not in f" {normalize(request.text)} ":
            return ()
        strong = [candidate for candidate in eligible if self._decision_score(candidate) >= self.config.parallel_threshold]
        if len(strong) < 2:
            return ()
        capability_owners: dict[str, tuple[str, float]] = {}
        for candidate in strong:
            for capability_id, score in candidate.capability_scores.items():
                if score < 0.5:
                    continue
                existing = capability_owners.get(capability_id)
                if existing is None or score > existing[1]:
                    capability_owners[capability_id] = (candidate.agent_id, score)
        selected = tuple(dict.fromkeys(owner for owner, _ in capability_owners.values()))
        return selected if len(selected) >= 2 else ()

    @staticmethod
    def _is_underspecified(text: str) -> bool:
        normalized = normalize(text)
        generic_markers = ("something not working", "need help", "does not work")
        informative_terms = {
            "account", "benefit", "bill", "charge", "delivery", "invoice", "leave",
            "network", "order", "parcel", "password", "payment", "policy", "refund",
            "salary", "security", "shipment", "subscription",
        }
        return any(marker in normalized for marker in generic_markers) and not (
            set(normalized.split()) & informative_terms
        )

    def _decide(
        self,
        request: RoutingRequest,
        candidates: tuple[CandidateEvaluation, ...],
        explicit_agent_id: str | None,
    ) -> tuple[DecisionOutcome, tuple[str, ...], tuple[str, ...], float | None, str]:
        by_id = {candidate.agent_id: candidate for candidate in candidates}
        if explicit_agent_id:
            explicit = by_id.get(explicit_agent_id)
            if explicit is None:
                return DecisionOutcome.CLARIFY, (), ("UNKNOWN_EXPLICIT_TARGET",), None, "The explicitly requested agent is not registered."
            if explicit.eligibility == Eligibility.ELIGIBLE:
                return DecisionOutcome.SELECT, (explicit.agent_id,), ("EXPLICIT_ELIGIBLE_TARGET",), None, "The explicitly requested agent is registered and eligible."
            if explicit.eligibility == Eligibility.REVIEW:
                return DecisionOutcome.ESCALATE, (), ("POLICY_REVIEW",), None, "The explicitly requested agent requires human review."
            return DecisionOutcome.ESCALATE, (), ("EXPLICIT_TARGET_BLOCKED",), None, "The explicitly requested agent is ineligible under the current policy or operational state."

        if self._is_underspecified(request.text):
            return DecisionOutcome.CLARIFY, (), ("UNDERSPECIFIED_REQUEST",), None, "The request does not contain enough domain or capability information to route safely."

        review = [candidate for candidate in candidates if candidate.eligibility == Eligibility.REVIEW]
        eligible = [candidate for candidate in candidates if candidate.eligibility == Eligibility.ELIGIBLE]
        if not eligible:
            if review:
                return DecisionOutcome.ESCALATE, (), ("POLICY_REVIEW", "NO_AUTONOMOUSLY_ELIGIBLE_AGENT"), None, "Candidate agents require human review."
            return DecisionOutcome.ABSTAIN, (), ("NO_ELIGIBLE_AGENT",), None, "No candidate agent is currently eligible."

        eligible.sort(key=lambda candidate: (-self._decision_score(candidate), candidate.agent_id))
        review.sort(key=lambda candidate: (-self._decision_score(candidate), candidate.agent_id))
        if review and self._decision_score(review[0]) >= self.config.selection_threshold:
            if self._decision_score(review[0]) >= self._decision_score(eligible[0]):
                return DecisionOutcome.ESCALATE, (), ("POLICY_REVIEW", "BEST_SUPPORTED_ROUTE_REQUIRES_REVIEW"), None, "The best-supported candidate requires human review."
        parallel = self._parallel_selection(request, eligible)
        if parallel:
            return DecisionOutcome.PARALLEL, parallel, ("MULTI_INTENT", "PARALLEL_CAPABILITY_COVERAGE"), None, "Multiple supported intents map to different eligible agents."

        best = eligible[0]
        best_score = self._decision_score(best)
        second_score = self._decision_score(eligible[1]) if len(eligible) > 1 else 0.0
        margin = round(best_score - second_score, 6) if len(eligible) > 1 else None

        if best_score < self.config.clarification_floor:
            return DecisionOutcome.ABSTAIN, (), ("LOW_ROUTING_SUPPORT",), margin, "No eligible candidate has sufficient routing support."
        if best_score < self.config.selection_threshold:
            return DecisionOutcome.CLARIFY, (), ("LOW_CALIBRATED_CONFIDENCE" if self.calibrator else "LOW_RAW_FIT",), margin, "The leading candidate is below the autonomous-selection threshold."
        if margin is not None and margin < self.config.margin_threshold:
            return DecisionOutcome.CLARIFY, (), ("AMBIGUOUS_MARGIN",), margin, "The leading candidates are too close for autonomous selection."
        threshold_code = "ABOVE_CALIBRATED_THRESHOLD" if self.calibrator else "ABOVE_RAW_FIT_THRESHOLD"
        return DecisionOutcome.SELECT, (best.agent_id,), ("ELIGIBLE_HIGHEST_DECISION_SCORE", threshold_code, "CLEAR_MARGIN"), margin, "The leading eligible candidate exceeds the configured threshold and decision margin."

    def route(
        self,
        request: RoutingRequest,
        *,
        decision_id: str | None = None,
        created_at: str | None = None,
    ) -> RouteResult:
        created_at = created_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
        decision_id = decision_id or f"rdr_{uuid.uuid4().hex}"
        explicit_agent_id = self.registry.detect_explicit_agent(request)
        retrieved = self.retriever.retrieve(request, self.registry, explicit_agent_id)
        candidates = tuple(
            self._evaluate_candidate(request, item, explicit_agent_id, created_at) for item in retrieved
        )
        outcome, selected, reason_codes, margin, explanation = self._decide(
            request, candidates, explicit_agent_id
        )
        content_hash = hashlib.sha256(request.text.encode("utf-8")).hexdigest()
        record = {
            "schema_version": self.config.schema_version,
            "decision_id": decision_id,
            "parent_workflow_id": request.metadata.get("parent_workflow_id"),
            "created_at": created_at,
            "environment": request.metadata.get("environment", "test"),
            "tenant_scope": request.metadata.get("tenant_scope"),
            "request": {
                "content_ref": request.content_ref or f"memory://requests/{request.request_id}",
                "content_sha256": content_hash,
                "locale": request.locale,
                "redacted": not bool(request.metadata.get("synthetic", False)),
                "representation": request.text if request.metadata.get("synthetic", False) else None,
            },
            "snapshots": {
                "context_version": request.metadata.get("context_version", "context@unversioned"),
                "registry_version": self.registry.version,
                "policy_bundle_version": self.policy_engine.version,
                "cost_model_version": self.registry.cost_model_version,
                "cost_unit": self.registry.cost_unit,
            },
            "evaluators": {
                "router_model": self.config.version,
                "router_prompt": "not-applicable:deterministic-reference-router",
                "feature_extractor": self.config.feature_version,
                "calibrator": self.calibrator.version if self.calibrator else None,
                "calibration_target": self.calibrator.target if self.calibrator else None,
                "calibration_cohort": self.calibrator.cohort if self.calibrator else None,
            },
            "candidate_retrieval": {
                "method": self.retriever.version,
                "version": self.retriever.version,
                "requested_k": self.retriever.top_k,
                "returned_k": len(candidates),
            },
            "candidates": [candidate.to_rdr_dict() for candidate in candidates],
            "decision": {
                "type": outcome.value,
                "selected_agent_ids": list(selected),
                "reason_codes": list(reason_codes),
                "human_explanation": explanation,
                "selection_threshold": self.config.selection_threshold,
                "top_two_margin": margin,
                "delegation_contract_ref": None,
                "execution_trace_ref": None,
                "outcome_ref": None,
            },
        }
        return RouteResult(request=request, candidates=candidates, record=record)

    def raw_candidate_observations(self, requests: Iterable[tuple[RoutingRequest, set[str]]]) -> list[tuple[float, int]]:
        observations: list[tuple[float, int]] = []
        for request, acceptable_agents in requests:
            result = self.route(request)
            for candidate in result.candidates:
                observations.append((candidate.raw_fit or 0.0, int(candidate.agent_id in acceptable_agents)))
        return observations
