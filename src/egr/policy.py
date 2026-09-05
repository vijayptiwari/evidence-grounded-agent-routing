from __future__ import annotations

from dataclasses import dataclass

from .models import AgentSpec, Eligibility, RoutingRequest


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    eligibility: Eligibility
    reason_codes: tuple[str, ...]
    rule_id: str


class DeterministicPolicyEngine:
    """Small reference policy engine kept outside the generative evaluator."""

    def __init__(self, version: str = "routing-policy@0.1.0"):
        self.version = version

    def evaluate(self, request: RoutingRequest, agent: AgentSpec) -> PolicyEvaluation:
        if agent.agent_id in request.blocked_agent_ids:
            return PolicyEvaluation(Eligibility.INELIGIBLE, ("POLICY_DENY",), "blocked-agent")
        if agent.agent_id in request.unavailable_agent_ids:
            return PolicyEvaluation(Eligibility.INELIGIBLE, ("TOOL_UNAVAILABLE",), "agent-unavailable")
        missing_tools = request.required_tools - set(agent.tools)
        if missing_tools:
            return PolicyEvaluation(
                Eligibility.INELIGIBLE,
                ("MISSING_REQUIRED_TOOL",),
                "required-tool",
            )
        if request.review_required or "human-review" in agent.policy_labels:
            return PolicyEvaluation(Eligibility.REVIEW, ("POLICY_REVIEW",), "human-review")
        return PolicyEvaluation(Eligibility.ELIGIBLE, ("POLICY_ALLOW",), "default-allow")
