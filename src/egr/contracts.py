from __future__ import annotations

import uuid
from datetime import UTC, datetime

from .models import DelegationContract, OutcomeEvent, RouteResult
from .registry import AgentRegistry


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def create_contracts(
    route: RouteResult,
    registry: AgentRegistry,
    *,
    objective: str,
    acceptance_criteria: tuple[str, ...],
    prohibited_actions: tuple[str, ...] = (),
    output_schema_ref: str | None = None,
    timeout_seconds: int = 120,
    max_retries: int = 1,
    created_at: str | None = None,
) -> tuple[DelegationContract, ...]:
    if not route.selected_agent_ids:
        raise ValueError("A route without selected agents cannot create a delegation contract")
    created_at = created_at or utc_now()
    contracts: list[DelegationContract] = []
    for agent_id in route.selected_agent_ids:
        agent = registry.get(agent_id)
        if agent is None:
            raise ValueError(f"Selected agent is absent from the registry: {agent_id}")
        contracts.append(
            DelegationContract(
                contract_id=f"contract_{uuid.uuid4().hex}",
                routing_decision_id=route.record["decision_id"],
                agent_id=agent_id,
                objective=objective,
                acceptance_criteria=acceptance_criteria,
                authorized_tools=agent.tools,
                prohibited_actions=prohibited_actions,
                output_schema_ref=output_schema_ref,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                policy_bundle_version=route.record["snapshots"]["policy_bundle_version"],
                created_at=created_at,
            )
        )
    return tuple(contracts)


def create_outcome(
    contract: DelegationContract,
    *,
    status: str,
    acceptance_passed: bool | None,
    evaluator_version: str,
    failure_class: str | None = None,
    evidence_refs: tuple[str, ...] = (),
    measured_at: str | None = None,
) -> OutcomeEvent:
    return OutcomeEvent(
        outcome_id=f"outcome_{uuid.uuid4().hex}",
        routing_decision_id=contract.routing_decision_id,
        contract_id=contract.contract_id,
        agent_id=contract.agent_id,
        status=status,
        acceptance_passed=acceptance_passed,
        failure_class=failure_class,
        measured_at=measured_at or utc_now(),
        evaluator_version=evaluator_version,
        evidence_refs=evidence_refs,
    )
