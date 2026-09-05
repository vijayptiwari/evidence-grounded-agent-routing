from __future__ import annotations

import operator
from typing import Annotated, Any, Callable, TypedDict

from ..models import RoutingRequest
from ..router import EvidenceGroundedRouter


class RoutingGraphState(TypedDict, total=False):
    request: RoutingRequest
    routing_decision: dict[str, Any]
    decision_type: str
    selected_agent_ids: list[str]
    dispatch_agent_id: str
    execution_events: Annotated[list[dict[str, Any]], operator.add]
    response: dict[str, Any]


Handler = Callable[[RoutingGraphState], dict[str, Any]]


def build_routing_graph(
    router: EvidenceGroundedRouter,
    *,
    agent_handler: Handler | None = None,
    clarification_handler: Handler | None = None,
    escalation_handler: Handler | None = None,
    abstention_handler: Handler | None = None,
):
    """Build a small LangGraph around an evidence-grounded routing node.

    `Send` creates one dispatch branch per selected agent. Real agent handlers
    should accept the contract—not the full raw routing state—and return a
    structured execution event.
    """

    try:
        from langgraph.graph import END, START, StateGraph
        from langgraph.types import Send
    except ImportError as error:
        raise RuntimeError(
            "LangGraph is optional. Install with `pip install -e .[langgraph]`."
        ) from error

    def route_node(state: RoutingGraphState) -> dict[str, Any]:
        result = router.route(state["request"])
        return {
            "routing_decision": result.record,
            "decision_type": result.outcome.value,
            "selected_agent_ids": list(result.selected_agent_ids),
        }

    def default_agent_handler(state: RoutingGraphState) -> dict[str, Any]:
        return {
            "execution_events": [
                {
                    "agent_id": state["dispatch_agent_id"],
                    "status": "dispatch-placeholder",
                    "routing_decision_id": state["routing_decision"]["decision_id"],
                }
            ]
        }

    def default_clarification(state: RoutingGraphState) -> dict[str, Any]:
        return {"response": {"status": "clarification_required", "decision": state["routing_decision"]}}

    def default_escalation(state: RoutingGraphState) -> dict[str, Any]:
        return {"response": {"status": "human_review_required", "decision": state["routing_decision"]}}

    def default_abstention(state: RoutingGraphState) -> dict[str, Any]:
        return {"response": {"status": "no_supported_route", "decision": state["routing_decision"]}}

    def next_steps(state: RoutingGraphState):
        decision = state["decision_type"]
        if decision in {"select", "parallel"}:
            return [
                Send(
                    "dispatch_agent",
                    {
                        **state,
                        "dispatch_agent_id": agent_id,
                    },
                )
                for agent_id in state["selected_agent_ids"]
            ]
        return {
            "clarify": "clarify",
            "escalate": "escalate",
            "abstain": "abstain",
        }[decision]

    builder = StateGraph(RoutingGraphState)
    builder.add_node("route", route_node)
    builder.add_node("dispatch_agent", agent_handler or default_agent_handler)
    builder.add_node("clarify", clarification_handler or default_clarification)
    builder.add_node("escalate", escalation_handler or default_escalation)
    builder.add_node("abstain", abstention_handler or default_abstention)
    builder.add_edge(START, "route")
    builder.add_conditional_edges("route", next_steps)
    builder.add_edge("dispatch_agent", END)
    builder.add_edge("clarify", END)
    builder.add_edge("escalate", END)
    builder.add_edge("abstain", END)
    return builder.compile()
