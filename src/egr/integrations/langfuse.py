from __future__ import annotations

from typing import Any

from ..models import RouteResult, RoutingRequest
from ..quality import evaluate_evidence_quality
from ..router import EvidenceGroundedRouter


def trace_route(
    router: EvidenceGroundedRouter,
    request: RoutingRequest,
    *,
    client: Any | None = None,
) -> RouteResult:
    """Route a request while emitting candidate-level Langfuse v4 observations.

    Raw request text is intentionally excluded. Configure Langfuse credentials
    through its documented environment variables or pass an initialized client.
    """

    if client is None:
        try:
            from langfuse import get_client
        except ImportError as error:
            raise RuntimeError(
                "Langfuse is optional. Install with `pip install -e .[langfuse]`."
            ) from error
        client = get_client()

    root_metadata = {
        "schema_version": router.config.schema_version,
        "router_version": router.config.version,
        "feature_version": router.config.feature_version,
        "registry_version": router.registry.version,
        "policy_bundle_version": router.policy_engine.version,
        "calibrator_version": router.calibrator.version if router.calibrator else None,
    }
    safe_input = {
        "request_id": request.request_id,
        "content_ref": request.content_ref,
        "locale": request.locale,
    }
    with client.start_as_current_observation(
        as_type="agent",
        name="evidence-grounded-routing",
        input=safe_input,
        metadata=root_metadata,
        version=router.config.version,
    ) as root:
        result = router.route(request)
        for candidate in result.candidates:
            with client.start_as_current_observation(
                as_type="evaluator",
                name="routing-candidate-evaluation",
                input={
                    "decision_id": result.record["decision_id"],
                    "agent_id": candidate.agent_id,
                    "agent_version": candidate.agent_version,
                },
                metadata={
                    "eligibility": candidate.eligibility.value,
                    "reason_codes": list(candidate.reason_codes),
                    "evidence_ids": [item.evidence_id for item in candidate.evidence],
                    "retrieval_rank": candidate.retrieval_rank,
                },
                version=router.config.feature_version,
            ) as observation:
                observation.update(
                    output={
                        "raw_fit": candidate.raw_fit,
                        "calibrated_success_probability": candidate.calibrated_success_probability,
                        "uncertainty": candidate.uncertainty,
                    }
                )
                if candidate.calibrated_success_probability is not None:
                    observation.score(
                        name="calibrated_success_probability",
                        value=candidate.calibrated_success_probability,
                        data_type="NUMERIC",
                    )

        quality = evaluate_evidence_quality(result.record)
        root.update(
            output={
                "decision_id": result.record["decision_id"],
                "decision_type": result.outcome.value,
                "selected_agent_ids": list(result.selected_agent_ids),
                "reason_codes": result.record["decision"]["reason_codes"],
            }
        )
        root.score(name="evidence_validity", value=quality.validity, data_type="NUMERIC")
        root.score(name="evidence_sufficiency", value=quality.sufficiency, data_type="NUMERIC")
        return result
