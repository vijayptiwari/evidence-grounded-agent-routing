from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from egr.integrations.langfuse import trace_route
from egr.integrations.langgraph import build_routing_graph
from egr.models import RoutingRequest
from egr.registry import AgentRegistry
from egr.router import EvidenceGroundedRouter


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("langgraph"), "LangGraph optional dependency is absent")
class LangGraphCompatibilityTests(unittest.TestCase):
    def test_single_and_parallel_dispatch(self) -> None:
        router = EvidenceGroundedRouter(AgentRegistry.from_path(ROOT / "configs" / "agents.json"))
        graph = build_routing_graph(router)
        single = graph.invoke(
            {
                "request": RoutingRequest(
                    request_id="langgraph-single",
                    text="Use the billing agent to explain this fee.",
                    metadata={"synthetic": True},
                ),
                "execution_events": [],
            }
        )
        self.assertEqual(single["decision_type"], "select")
        self.assertEqual(len(single["execution_events"]), 1)

        parallel = graph.invoke(
            {
                "request": RoutingRequest(
                    request_id="langgraph-parallel",
                    text="Check my refund status and track my order.",
                    metadata={"synthetic": True},
                ),
                "execution_events": [],
            }
        )
        self.assertEqual(parallel["decision_type"], "parallel")
        self.assertEqual(len(parallel["execution_events"]), 2)


@unittest.skipUnless(importlib.util.find_spec("langfuse"), "Langfuse optional dependency is absent")
class LangfuseCompatibilityTests(unittest.TestCase):
    def test_real_v4_client_accepts_observations_without_export(self) -> None:
        from langfuse import Langfuse

        client = Langfuse(
            public_key="pk-lf-offline-test",
            secret_key="sk-lf-offline-test",
            base_url="http://127.0.0.1:9",
            tracing_enabled=False,
        )
        router = EvidenceGroundedRouter(AgentRegistry.from_path(ROOT / "configs" / "agents.json"))
        result = trace_route(
            router,
            RoutingRequest(
                request_id="langfuse-real-client",
                text="private customer text about a refund",
                content_ref="secure://requests/langfuse-real-client",
            ),
            client=client,
        )
        client.flush()
        self.assertTrue(result.record["decision_id"])


if __name__ == "__main__":
    unittest.main()
