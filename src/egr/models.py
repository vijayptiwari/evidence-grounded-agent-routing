from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Eligibility(StrEnum):
    ELIGIBLE = "eligible"
    REVIEW = "review"
    INELIGIBLE = "ineligible"


class DecisionOutcome(StrEnum):
    SELECT = "select"
    PARALLEL = "parallel"
    CLARIFY = "clarify"
    ABSTAIN = "abstain"
    ESCALATE = "escalate"


@dataclass(frozen=True, slots=True)
class Capability:
    capability_id: str
    description: str
    keywords: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Capability":
        return cls(
            capability_id=value["capability_id"],
            description=value["description"],
            keywords=tuple(value.get("keywords", [])),
        )


@dataclass(frozen=True, slots=True)
class AgentSpec:
    agent_id: str
    version: str
    description: str
    aliases: tuple[str, ...]
    domains: tuple[str, ...]
    capabilities: tuple[Capability, ...]
    tools: tuple[str, ...] = ()
    policy_labels: tuple[str, ...] = ()
    expected_cost: float = 0.0
    expected_latency_ms: float = 0.0
    empirical_success_rate: float | None = None
    empirical_sample_size: int = 0
    empirical_window: str | None = None
    empirical_source_ref: str | None = None
    empirical_method: str = "declared-historical-success-rate"
    empirical_outcome_definition: str = "unspecified"
    empirical_source_type: str = "asserted"
    empirical_trust_tier: str = "self_asserted"
    empirical_freshness: str = "unknown"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AgentSpec":
        return cls(
            agent_id=value["agent_id"],
            version=value["version"],
            description=value["description"],
            aliases=tuple(value.get("aliases", [])),
            domains=tuple(value.get("domains", [])),
            capabilities=tuple(Capability.from_dict(item) for item in value.get("capabilities", [])),
            tools=tuple(value.get("tools", [])),
            policy_labels=tuple(value.get("policy_labels", [])),
            expected_cost=float(value.get("expected_cost", 0.0)),
            expected_latency_ms=float(value.get("expected_latency_ms", 0.0)),
            empirical_success_rate=value.get("empirical_success_rate"),
            empirical_sample_size=int(value.get("empirical_sample_size", 0)),
            empirical_window=value.get("empirical_window"),
            empirical_source_ref=value.get("empirical_source_ref"),
            empirical_method=value.get("empirical_method", "declared-historical-success-rate"),
            empirical_outcome_definition=value.get("empirical_outcome_definition", "unspecified"),
            empirical_source_type=value.get("empirical_source_type", "asserted"),
            empirical_trust_tier=value.get("empirical_trust_tier", "self_asserted"),
            empirical_freshness=value.get("empirical_freshness", "unknown"),
        )


@dataclass(frozen=True, slots=True)
class RoutingRequest:
    request_id: str
    text: str
    locale: str = "en"
    content_ref: str | None = None
    explicit_agent_id: str | None = None
    blocked_agent_ids: frozenset[str] = field(default_factory=frozenset)
    unavailable_agent_ids: frozenset[str] = field(default_factory=frozenset)
    required_tools: frozenset[str] = field(default_factory=frozenset)
    review_required: bool = False
    allow_parallel: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    evidence_id: str
    family: str
    source_type: str
    source_ref: str
    source_version: str
    method: str
    observed_at: str
    trust_tier: str
    freshness: str
    raw_value: Any
    query_span: str | None = None
    capability_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    agent_id: str
    agent_version: str
    retrieval_rank: int | None
    retrieval_score: float | None
    eligibility: Eligibility
    reason_codes: tuple[str, ...]
    evidence: tuple[EvidenceItem, ...]
    raw_fit: float | None
    calibrated_success_probability: float | None
    uncertainty: float | None
    expected_cost: float | None
    expected_latency_ms: float | None
    capability_scores: dict[str, float] = field(default_factory=dict)

    def to_rdr_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "retrieval_rank": self.retrieval_rank,
            "retrieval_score": self.retrieval_score,
            "eligibility": self.eligibility.value,
            "reason_codes": list(self.reason_codes),
            "evidence": [item.to_dict() for item in self.evidence],
            "raw_fit": self.raw_fit,
            "calibrated_success_probability": self.calibrated_success_probability,
            "uncertainty": self.uncertainty,
            "expected_cost": self.expected_cost,
            "expected_latency_ms": self.expected_latency_ms,
        }


@dataclass(frozen=True, slots=True)
class RouteResult:
    request: RoutingRequest
    candidates: tuple[CandidateEvaluation, ...]
    record: dict[str, Any]

    @property
    def outcome(self) -> DecisionOutcome:
        return DecisionOutcome(self.record["decision"]["type"])

    @property
    def selected_agent_ids(self) -> tuple[str, ...]:
        return tuple(self.record["decision"]["selected_agent_ids"])


@dataclass(frozen=True, slots=True)
class DelegationContract:
    contract_id: str
    routing_decision_id: str
    agent_id: str
    objective: str
    acceptance_criteria: tuple[str, ...]
    authorized_tools: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    output_schema_ref: str | None
    timeout_seconds: int
    max_retries: int
    policy_bundle_version: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OutcomeEvent:
    outcome_id: str
    routing_decision_id: str
    contract_id: str
    agent_id: str
    status: str
    acceptance_passed: bool | None
    failure_class: str | None
    measured_at: str
    evaluator_version: str
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
