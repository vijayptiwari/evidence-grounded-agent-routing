from __future__ import annotations

import argparse
import json
from contextlib import ExitStack
from importlib.resources import as_file, files
from pathlib import Path

from .benchmark import run_benchmark
from .models import RoutingRequest
from .registry import AgentRegistry
from .replay import ReplayBundle, replay
from .router import EvidenceGroundedRouter


def _write_or_print(payload: object, output: str | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote output to {path}")
    else:
        print(rendered)


def _input_path(value: str | None, bundled_name: str, stack: ExitStack) -> Path:
    if value:
        return Path(value)
    resource = files("egr.data").joinpath(bundled_name)
    return Path(stack.enter_context(as_file(resource)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="egr", description="Evidence-grounded routing reference CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    route_parser = subparsers.add_parser("route", help="Route one synthetic or redacted request")
    route_parser.add_argument("text")
    route_parser.add_argument("--request-id", default="cli-request")
    route_parser.add_argument("--registry", help="registry JSON path; defaults to the bundled synthetic registry")
    route_parser.add_argument("--explicit-agent")
    route_parser.add_argument("--output")
    route_parser.add_argument("--synthetic", action="store_true")

    benchmark_parser = subparsers.add_parser("benchmark", help="Run the synthetic smoke benchmark")
    benchmark_parser.add_argument("--registry", help="registry JSON path; defaults to the bundled synthetic registry")
    benchmark_parser.add_argument("--cases", help="case JSONL path; defaults to the bundled synthetic benchmark")
    benchmark_parser.add_argument("--output")
    benchmark_parser.add_argument(
        "--external",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Add pinned JSONL predictions from an external LLM or learned router",
    )

    replay_parser = subparsers.add_parser("replay-demo", help="Demonstrate deterministic replay")
    replay_parser.add_argument("text")
    replay_parser.add_argument("--registry", help="registry JSON path; defaults to the bundled synthetic registry")

    args = parser.parse_args(argv)
    with ExitStack() as resources:
        registry_path = _input_path(args.registry, "agents.json", resources)
        registry = AgentRegistry.from_path(registry_path)

        if args.command == "route":
            router = EvidenceGroundedRouter(registry)
            result = router.route(
                RoutingRequest(
                    request_id=args.request_id,
                    text=args.text,
                    explicit_agent_id=args.explicit_agent,
                    metadata={"synthetic": args.synthetic},
                )
            )
            _write_or_print(result.record, args.output)
            return 0

        if args.command == "benchmark":
            cases_path = _input_path(args.cases, "benchmark_cases.jsonl", resources)
            external = dict(item.split("=", 1) for item in args.external)
            report = run_benchmark(registry_path, cases_path, external)
            _write_or_print(report, args.output)
            return 0

        router = EvidenceGroundedRouter(registry)
        original = router.route(
            RoutingRequest(request_id="replay-demo", text=args.text, metadata={"synthetic": True}),
            decision_id="rdr_replay_demo",
            created_at="2026-09-05T00:00:00Z",
        )
        report = replay(ReplayBundle.capture(original), router)
        _write_or_print(
            {
                "exact_match": report.exact_match,
                "original_sha256": report.original_sha256,
                "replayed_sha256": report.replayed_sha256,
                "differences": list(report.differences),
            },
            None,
        )
        return 0
