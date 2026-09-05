"""Evidence-grounded agent routing reference implementation."""

from .calibration import PlattCalibrator
from .models import AgentSpec, DecisionOutcome, Eligibility, RoutingRequest
from .router import EvidenceGroundedRouter, RouterConfig

__all__ = [
    "AgentSpec",
    "DecisionOutcome",
    "Eligibility",
    "EvidenceGroundedRouter",
    "PlattCalibrator",
    "RouterConfig",
    "RoutingRequest",
]

__version__ = "0.1.0"
