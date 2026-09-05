# Release checklist

Use this checklist for a public GitHub release. A checked item should point to evidence whenever possible.

## Public metadata

- [ ] Confirm the public author name and GitHub profile.
- [ ] Set the final repository owner and slug; add the Git remote and project URLs.
- [ ] Add `CITATION.cff` with the release’s preferred paper citation.
- [ ] Apply the approved code and documentation licenses and state their scopes in the README.
- [ ] Remove all public placeholders with `python scripts/verify.py --release`.

## Artifact quality

- [ ] Freeze the paper, schemas, registry, benchmark, and implementation for the tag.
- [ ] Run `python scripts/verify.py` in a clean Python 3.11+ environment.
- [ ] Run the optional adapter tests with `requirements-optional-tested.txt`.
- [ ] Build the source distribution and wheel with `python -m build`.
- [ ] Validate distribution metadata with `python -m twine check dist/*`.
- [ ] Review the generated benchmark result and confirm the research boundary remains prominent.
- [ ] Inspect the rendered Markdown on GitHub, including diagrams, anchors, code blocks, and local links.
- [ ] Review the repository for credentials, private data, local paths, draft notes, and generated clutter.
- [ ] Review the contribution, conduct, support, governance, and security policies for the release.

## GitHub setup

- [ ] Protect `main` and require the test workflow before merge.
- [ ] Enable private vulnerability reporting.
- [ ] Enable Dependabot alerts and updates.
- [ ] Choose whether to enable Discussions.
- [ ] Add topics such as `agentic-ai`, `agent-routing`, `langgraph`, `llm-evaluation`, and `decision-provenance`.
- [ ] Create a signed or annotated `v0.1.0` tag from the reviewed commit.
- [ ] Create a GitHub Release using the changelog entry and attach any rendered paper artifact.

## Preservation and announcement

- [ ] Connect the repository to Zenodo before creating the archival release if a DOI is desired.
- [ ] Add the DOI to `CITATION.cff`, README, and paper after it resolves.
- [ ] Use the bounded portfolio and launch wording in `PORTFOLIO_ENTRY.md`.
- [ ] Record known limitations and the next empirical milestone in the release notes.

Publishing the repository and creating the archival release are deliberate maintainer actions; the verification script does not perform either one.
