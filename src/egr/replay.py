from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .models import RouteResult, RoutingRequest
from .router import EvidenceGroundedRouter
from .store import digest


@dataclass(frozen=True, slots=True)
class ReplayBundle:
    request: dict[str, Any]
    original_record: dict[str, Any]

    @classmethod
    def capture(cls, result: RouteResult) -> "ReplayBundle":
        request = asdict(result.request)
        request["blocked_agent_ids"] = sorted(request["blocked_agent_ids"])
        request["unavailable_agent_ids"] = sorted(request["unavailable_agent_ids"])
        request["required_tools"] = sorted(request["required_tools"])
        return cls(request=request, original_record=result.record)

    def routing_request(self) -> RoutingRequest:
        value = dict(self.request)
        value["blocked_agent_ids"] = frozenset(value.get("blocked_agent_ids", []))
        value["unavailable_agent_ids"] = frozenset(value.get("unavailable_agent_ids", []))
        value["required_tools"] = frozenset(value.get("required_tools", []))
        return RoutingRequest(**value)


@dataclass(frozen=True, slots=True)
class ReplayReport:
    exact_match: bool
    original_sha256: str
    replayed_sha256: str
    differences: tuple[str, ...]
    replayed_record: dict[str, Any]


def replay(bundle: ReplayBundle, router: EvidenceGroundedRouter) -> ReplayReport:
    original = bundle.original_record
    rerun = router.route(
        bundle.routing_request(),
        decision_id=original["decision_id"],
        created_at=original["created_at"],
    ).record
    differences: list[str] = []
    checks = {
        "registry_version": (
            original["snapshots"]["registry_version"],
            rerun["snapshots"]["registry_version"],
        ),
        "policy_bundle_version": (
            original["snapshots"]["policy_bundle_version"],
            rerun["snapshots"]["policy_bundle_version"],
        ),
        "router_model": (
            original["evaluators"]["router_model"],
            rerun["evaluators"]["router_model"],
        ),
        "feature_extractor": (
            original["evaluators"]["feature_extractor"],
            rerun["evaluators"]["feature_extractor"],
        ),
        "calibrator": (
            original["evaluators"]["calibrator"],
            rerun["evaluators"]["calibrator"],
        ),
        "decision_type": (original["decision"]["type"], rerun["decision"]["type"]),
        "selected_agents": (
            original["decision"]["selected_agent_ids"],
            rerun["decision"]["selected_agent_ids"],
        ),
    }
    for field, (before, after) in checks.items():
        if before != after:
            differences.append(f"{field}: {before!r} -> {after!r}")
    original_digest = digest(original)
    rerun_digest = digest(rerun)
    if original_digest != rerun_digest and not differences:
        differences.append("Record content differs outside the summarized replay fields")
    return ReplayReport(
        exact_match=original_digest == rerun_digest,
        original_sha256=original_digest,
        replayed_sha256=rerun_digest,
        differences=tuple(differences),
        replayed_record=rerun,
    )
