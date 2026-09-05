from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenceQualityReport:
    validity: float
    sufficiency: float
    invalid_evidence_ids: tuple[str, ...]
    missing_requirements: tuple[str, ...]


def evaluate_evidence_quality(record: dict[str, Any]) -> EvidenceQualityReport:
    """Evaluate auditable record properties, not truth in the external world.

    `validity` checks whether evidence is structurally attributable and current.
    `sufficiency` checks whether selected candidates have the minimum independent
    evidence families required by this reference policy. Neither metric proves
    that a source's substantive claim is correct.
    """

    evidence = [item for candidate in record.get("candidates", []) for item in candidate.get("evidence", [])]
    invalid: list[str] = []
    for item in evidence:
        required = ("evidence_id", "family", "source_type", "source_ref", "source_version", "method")
        if any(not item.get(field) for field in required) or item.get("freshness") in {"stale", "expired"}:
            invalid.append(item.get("evidence_id", "<missing-id>"))
    validity = 1.0 if not evidence else 1.0 - len(invalid) / len(evidence)

    candidates = {item["agent_id"]: item for item in record.get("candidates", [])}
    missing: list[str] = []
    for agent_id in record.get("decision", {}).get("selected_agent_ids", []):
        candidate = candidates.get(agent_id)
        if candidate is None:
            missing.append(f"{agent_id}:candidate")
            continue
        families = {item.get("family") for item in candidate.get("evidence", [])}
        if candidate.get("eligibility") != "eligible" or "policy" not in families:
            missing.append(f"{agent_id}:eligibility")
        if not ({"request", "registry"} & families):
            missing.append(f"{agent_id}:fit-evidence")
        if not candidate.get("reason_codes"):
            missing.append(f"{agent_id}:reason-codes")
    total_requirements = max(1, len(record.get("decision", {}).get("selected_agent_ids", [])) * 3)
    sufficiency = max(0.0, 1.0 - len(missing) / total_requirements)
    if not record.get("decision", {}).get("selected_agent_ids"):
        sufficiency = 1.0 if record.get("decision", {}).get("reason_codes") else 0.0

    return EvidenceQualityReport(
        validity=round(validity, 6),
        sufficiency=round(sufficiency, 6),
        invalid_evidence_ids=tuple(invalid),
        missing_requirements=tuple(missing),
    )
