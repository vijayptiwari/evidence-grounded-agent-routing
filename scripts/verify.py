#!/usr/bin/env python3
"""Run the repository's reproducibility and publication-readiness checks."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
EXCLUDED_PARTS = {".git", ".venv", "build", "dist", "research", "__pycache__"}
LOCAL_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
VERSION_PATTERN = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
PUBLIC_PLACEHOLDERS = {
    "[Author]": "public author name",
    "[GitHub repository URL]": "final repository URL",
    "https://example.org/": "permanent identifier",
    "Replace bracketed fields before publishing.": "finished portfolio copy",
}


class VerificationFailure(RuntimeError):
    pass


def public_files(suffixes: set[str] | None = None) -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts):
            continue
        if suffixes is None or path.suffix.lower() in suffixes:
            files.append(path)
    return sorted(files)


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    rendered = " ".join(command)
    print(f"[run] {rendered}", flush=True)
    completed = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if completed.returncode:
        raise VerificationFailure(f"Command failed with exit code {completed.returncode}: {rendered}")


def verify_versions() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_version = metadata["project"]["version"]
    match = VERSION_PATTERN.search((SRC / "egr" / "__init__.py").read_text(encoding="utf-8"))
    if not match or match.group(1) != package_version:
        raise VerificationFailure("pyproject.toml and egr.__version__ disagree")

    schema_ids: set[str] = set()
    for path in sorted((ROOT / "schemas").glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema_id = schema.get("$id", "")
        if not schema_id.startswith("urn:egr:schema:"):
            raise VerificationFailure(f"{path.relative_to(ROOT)} has a non-project schema $id")
        if schema_id in schema_ids:
            raise VerificationFailure(f"Duplicate schema $id: {schema_id}")
        schema_ids.add(schema_id)
    registry_copy = ROOT / "configs" / "agents.json"
    bundled_registry = SRC / "egr" / "data" / "agents.json"
    if json.loads(registry_copy.read_text(encoding="utf-8")) != json.loads(bundled_registry.read_text(encoding="utf-8")):
        raise VerificationFailure("Bundled CLI registry drifted from configs/agents.json")

    case_copy = ROOT / "benchmark" / "cases.jsonl"
    bundled_cases = SRC / "egr" / "data" / "benchmark_cases.jsonl"
    parse_jsonl = lambda path: [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if parse_jsonl(case_copy) != parse_jsonl(bundled_cases):
        raise VerificationFailure("Bundled CLI cases drifted from benchmark/cases.jsonl")
    print(f"[ok] package version {package_version}; {len(schema_ids)} unique schema identifiers")


def verify_schemas() -> None:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise VerificationFailure('Schema checks require `python -m pip install -e ".[dev]"`') from exc

    pairs = (
        ("routing-decision.schema.json", "routing-decision.example.json", False),
        ("delegation-contract.schema.json", "delegation-contract.example.json", False),
        ("outcome-event.schema.json", "outcome-event.example.json", False),
        ("record-envelope.schema.json", "record-envelope.example.json", False),
        ("external-prediction.schema.json", "external-prediction.example.jsonl", True),
    )
    for schema_name, example_name, is_jsonl in pairs:
        schema_path = ROOT / "schemas" / schema_name
        example_path = ROOT / "examples" / example_name
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        text = example_path.read_text(encoding="utf-8")
        instances = [json.loads(line) for line in text.splitlines() if line.strip()] if is_jsonl else [json.loads(text)]
        for index, instance in enumerate(instances, start=1):
            errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
            if errors:
                locations = ", ".join("/".join(map(str, error.path)) or "<root>" for error in errors[:3])
                raise VerificationFailure(f"{example_name} fails {schema_name} at {locations}")
    print(f"[ok] {len(pairs)} schemas and their examples validate under JSON Schema Draft 2020-12")


def verify_markdown() -> None:
    markdown_files = public_files({".md"})
    broken: list[str] = []
    unbalanced: list[str] = []
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        fences = [line for line in text.splitlines() if re.match(r"^\s*(```|~~~)", line)]
        if len(fences) % 2:
            unbalanced.append(str(path.relative_to(ROOT)))
        for raw_target in LOCAL_LINK.findall(text):
            target = raw_target.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            target = target.split(" ", 1)[0]
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                broken.append(f"{path.relative_to(ROOT)} -> {raw_target} (outside repository)")
                continue
            if not resolved.exists():
                broken.append(f"{path.relative_to(ROOT)} -> {raw_target}")
    if unbalanced:
        raise VerificationFailure("Unbalanced Markdown fences: " + ", ".join(unbalanced))
    if broken:
        raise VerificationFailure("Broken local Markdown links:\n  " + "\n  ".join(broken))
    print(f"[ok] {len(markdown_files)} Markdown files have balanced fences and resolvable local links")


def verify_public_hygiene(*, release: bool) -> None:
    text_files = public_files({".md", ".py", ".toml", ".json", ".jsonl", ".yml", ".yaml", ".txt"})
    local_paths: list[str] = []
    placeholders: list[str] = []
    secret_markers: list[str] = []
    suspicious = re.compile(r"(?i)(?:AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")
    for path in text_files:
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8")
        relative = str(path.relative_to(ROOT))
        if re.search(r"(?i)[A-Z]:\\Users\\", text):
            local_paths.append(relative)
        if suspicious.search(text):
            secret_markers.append(relative)
        for placeholder in PUBLIC_PLACEHOLDERS:
            if placeholder in text:
                placeholders.append(f"{relative}: {PUBLIC_PLACEHOLDERS[placeholder]}")

    if local_paths:
        raise VerificationFailure("Public files contain local Windows user paths: " + ", ".join(local_paths))
    if secret_markers:
        raise VerificationFailure("Possible private-key or access-key material in: " + ", ".join(secret_markers))
    if placeholders and release:
        raise VerificationFailure("Unresolved publication placeholders:\n  " + "\n  ".join(placeholders))
    if placeholders:
        print("[warn] release metadata remains unresolved:\n  " + "\n  ".join(placeholders))
    else:
        print("[ok] no known public placeholders")
    print("[ok] no local Windows user paths or high-confidence key markers found in public text")


def verify_release_metadata() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    missing: list[str] = []
    if not metadata.get("authors"):
        missing.append("pyproject.toml project.authors")
    if not metadata.get("license"):
        missing.append("pyproject.toml project.license")
    if not metadata.get("urls", {}).get("Repository"):
        missing.append("pyproject.toml project.urls.Repository")
    if not (ROOT / "CITATION.cff").exists():
        missing.append("CITATION.cff")
    if not (ROOT / "LICENSE.md").exists():
        missing.append("LICENSE.md")
    if not (ROOT / "LICENSES" / "Apache-2.0.txt").exists():
        missing.append("LICENSES/Apache-2.0.txt")
    if not (ROOT / "LICENSES" / "CC-BY-4.0.txt").exists():
        missing.append("LICENSES/CC-BY-4.0.txt")
    if missing:
        raise VerificationFailure("Missing release metadata: " + ", ".join(missing))

    completed = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode or not completed.stdout.strip():
        raise VerificationFailure("Git remote `origin` is not configured")
    print("[ok] author, license, citation, repository URL, and Git remote metadata are present")


def verify_benchmark() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    with tempfile.TemporaryDirectory(prefix="egr-verify-") as directory:
        output = Path(directory) / "benchmark.json"
        run(
            [
                sys.executable,
                "-m",
                "egr.benchmark",
                "--registry",
                "configs/agents.json",
                "--cases",
                "benchmark/cases.jsonl",
                "--output",
                str(output),
            ],
            env=env,
        )
        report = json.loads(output.read_text(encoding="utf-8"))
    if report.get("calibration_cases") != 12:
        raise VerificationFailure("Benchmark no longer reports the declared 12 calibration cases")
    if report.get("test_cases") != 30:
        raise VerificationFailure("Benchmark no longer reports the declared 30 evaluation cases")
    expected_results = {"evidence-grounded", "fixed-weight-score-only", "keyword-baseline", "similarity-top1-baseline"}
    if not expected_results.issubset(report.get("results", {})):
        raise VerificationFailure("Benchmark is missing one or more declared predictors")
    full = report["results"]["evidence-grounded"]
    if full.get("constraint_violation_rate") != 0.0:
        raise VerificationFailure("Evidence-grounded smoke run has a non-zero constraint violation rate")
    if "Synthetic" not in report.get("research_boundary", ""):
        raise VerificationFailure("Benchmark output lost its synthetic-data research boundary")
    print("[ok] benchmark regenerates with 12 calibration cases, 30 evaluation cases, declared predictors, and safety boundary")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", action="store_true", help="also require final public identity, license, citation, and remote metadata")
    parser.add_argument("--skip-tests", action="store_true", help="skip unit tests when a CI matrix already ran them")
    args = parser.parse_args()

    try:
        verify_versions()
        verify_schemas()
        verify_markdown()
        verify_public_hygiene(release=args.release)
        verify_benchmark()
        if not args.skip_tests:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(SRC)
            run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], env=env)
        if args.release:
            verify_release_metadata()
    except VerificationFailure as exc:
        print(f"[failed] {exc}", file=sys.stderr)
        return 1

    mode = "release" if args.release else "development"
    print(f"[passed] {mode} verification completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
