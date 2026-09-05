# Contributing

Thank you for helping improve Evidence-Grounded Agent Routing. Contributions are welcome when they preserve the project’s central separation between evidence, eligibility, uncertainty, utility, and execution outcome.

## Before opening a change

- Use an issue for a behavior change, schema change, new evidence family, or empirical claim.
- Keep private, customer, credential, and production data out of issues, fixtures, traces, and commits.
- Label synthetic examples as synthetic. Do not present development-set results as independent validation.
- Prefer a small, reviewable pull request with a clear falsifiable reason for the change.

## Development setup

Python 3.11 or newer is required.

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/verify.py
```

To exercise the optional adapters with the exact versions used for this release:

```bash
python -m pip install -r requirements-optional-tested.txt
python -m unittest tests/test_optional_integrations.py -v
```

## Change requirements

Code changes should include tests for the intended behavior and at least one relevant failure mode. Schema changes must update the corresponding example and version field. Benchmark changes must explain whether they alter cases, labels, metrics, thresholds, or only presentation.

Research or documentation changes should distinguish among:

- a statement supported by a cited external source;
- a design choice made by this project;
- a result reproduced by the included software; and
- a hypothesis that still requires independent empirical evaluation.

Do not add “first,” “novel,” “state of the art,” safety, compliance, or production-improvement claims without a documented search method and evidence strong enough to support that wording.

## Pull requests

Before requesting review, run:

```bash
python scripts/verify.py
```

Use `python scripts/verify.py --release` when preparing a tag. The release mode also checks public metadata and unresolved placeholders.

By contributing, you agree that your contribution is distributed under the licenses declared by this repository for the affected code or documentation.
