from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import exp, log
from typing import Iterable


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = exp(-value)
        return 1.0 / (1.0 + z)
    z = exp(value)
    return z / (1.0 + z)


@dataclass(frozen=True, slots=True)
class PlattCalibrator:
    """Small dependency-free logistic calibrator for one-dimensional raw scores.

    This is a reference implementation. Production calibration should include
    data-splitting, cohort checks, uncertainty intervals, and drift monitoring.
    """

    slope: float
    intercept: float
    trained_examples: int
    version: str
    target: str
    cohort: str

    @classmethod
    def fit(
        cls,
        observations: Iterable[tuple[float, int]],
        *,
        iterations: int = 2_000,
        learning_rate: float = 0.05,
        l2: float = 0.001,
        target: str = "candidate_success",
        cohort: str = "unspecified",
    ) -> "PlattCalibrator":
        data = [(float(score), int(label)) for score, label in observations]
        if len(data) < 4 or {label for _, label in data} != {0, 1}:
            raise ValueError("Calibration requires at least four examples and both labels")

        positives = sum(label for _, label in data)
        negatives = len(data) - positives
        slope = 1.0
        intercept = log((positives + 1.0) / (negatives + 1.0))

        for _ in range(iterations):
            slope_gradient = 0.0
            intercept_gradient = 0.0
            for score, label in data:
                probability = _sigmoid(slope * score + intercept)
                error = probability - label
                slope_gradient += error * score
                intercept_gradient += error
            scale = 1.0 / len(data)
            slope -= learning_rate * (slope_gradient * scale + l2 * slope)
            intercept -= learning_rate * intercept_gradient * scale

        fingerprint = sha256(
            f"{slope:.12f}|{intercept:.12f}|{len(data)}|{target}|{cohort}".encode("utf-8")
        ).hexdigest()[:12]
        return cls(
            slope=slope,
            intercept=intercept,
            trained_examples=len(data),
            version=f"platt-{fingerprint}",
            target=target,
            cohort=cohort,
        )

    def predict(self, raw_score: float) -> float:
        return _sigmoid(self.slope * float(raw_score) + self.intercept)

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "slope": self.slope,
            "intercept": self.intercept,
            "trained_examples": self.trained_examples,
            "version": self.version,
            "target": self.target,
            "cohort": self.cohort,
        }
