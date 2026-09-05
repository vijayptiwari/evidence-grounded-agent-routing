# Security policy

## Supported versions

The most recent `0.1.x` release is the only supported line while the project remains an alpha research reference implementation. Support means best-effort assessment and remediation; it is not a service-level commitment.

## Reporting a vulnerability

Use GitHub’s private vulnerability-reporting channel for this repository. If that channel is unavailable, contact the repository owner privately through the GitHub profile instead of opening a public issue.

Do not include credentials, personal data, proprietary prompts, customer records, or unredacted production traces in a report. A minimal synthetic reproducer is preferred.

Please include the affected version or commit, the impact, reproduction steps, and any suggested mitigation. The maintainer will acknowledge a report when practicable, validate its scope, and coordinate disclosure after a fix or documented mitigation is available.

## Security boundaries

This repository is a research scaffold, not a complete security control. In particular:

- deterministic policy gates do not replace authorization enforcement at tool and data boundaries;
- a SHA-256 hash chain detects record modification but does not provide signatures, trusted timestamps, durable storage, or non-repudiation;
- source-linked evidence can still be false, stale, poisoned, or insufficient;
- optional observability integrations require independent privacy, access-control, and retention configuration; and
- the included synthetic benchmark does not establish resistance to production attacks.

Deployers are responsible for threat modeling, secrets management, tenant isolation, least privilege, data minimization, incident response, and testing in their own environment.
