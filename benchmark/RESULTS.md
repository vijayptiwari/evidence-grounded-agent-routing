# Synthetic smoke-test results

These results verify that the benchmark, metrics, gates, calibration, and ablations execute. They do not estimate real-world performance. The implementation was developed while inspecting this synthetic dataset, so it is not an independent held-out test.

## Current run

The run uses 12 calibration cases and 30 synthetic smoke-evaluation cases across six agents.

The full evidence-grounded configuration produced:

- route-decision accuracy: **0.9667**;
- autonomous coverage: **0.6000**;
- selective risk on autonomous routes: **0.0556**;
- constraint-violation rate: **0.0000**;
- candidate recall at `k=5`: **1.0000**;
- Brier score: **0.0694**;
- Expected Calibration Error: **0.1118**; and
- automated evidence validity and minimum sufficiency: **1.0000** each.

Baseline route-decision accuracy was:

- keyword matching: **0.3333**;
- similarity top-1: **0.5667**; and
- the corrected `20/30/40/10` score-only design: **0.5667**.

The harness produced a route-accuracy bootstrap interval of **[0.9000, 1.0000]** and a paired accuracy difference of **0.4000** against the score-only baseline, with a bootstrap interval of **[0.2333, 0.6000]**. These calculations verify the statistical code. Because this is a small, contaminated synthetic development set, the intervals do not support population-level or confirmatory inference.

The generated risk-coverage curve reaches zero observed selective risk at thresholds of `0.70` and above, while coverage falls to `0.1667` or less. This illustrates the intended tradeoff but is far too small and artificial for threshold selection.

## What the ablations demonstrate

- Removing capability evidence reduced smoke route accuracy to **0.4333** and autonomous coverage to **0.0667**.
- Removing the policy gate increased the measured constraint-violation rate to **0.2333**.
- Removing operational eligibility increased the violation rate to **0.1000**.
- Alias and synthetic empirical-prior removal did not change route accuracy on this small dataset, indicating that these features add no demonstrated value here.

The last result matters: the framework must be willing to discover that a proposed evidence family is redundant. On this dataset, capability descriptions dominate alias and empirical signals.

## Known failure

One intentionally ambiguous case involving a charge for a purchase was routed to the order agent rather than clarified. It remains in the dataset as a visible failure instead of being rewritten to match the system.

## Reproduction

```bash
PYTHONPATH=src python -m egr benchmark --output benchmark/results/latest.json
```

The machine-readable output includes every per-case result and every ablation configuration.
