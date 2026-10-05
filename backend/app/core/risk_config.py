"""Central, configurable risk classification.

Thresholds are NOT hardcoded across the app — everything imports from here.
They map a continuous `risk_probability` in [0, 1] to a discrete risk level,
and a predicted final score to the same scale, so both signals agree.

    risk_probability <  low_boundary              -> LOW
    low_boundary <= risk_probability <  medium    -> MEDIUM
    medium_boundary <= risk_probability < high    -> HIGH
    risk_probability >= high_boundary             -> CRITICAL
"""
from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class RiskThresholds:
    low: float
    medium: float
    high: float

    def classify(self, risk_probability: float) -> str:
        p = max(0.0, min(1.0, float(risk_probability)))
        if p >= self.high:
            return "CRITICAL"
        if p >= self.medium:
            return "HIGH"
        if p >= self.low:
            return "MEDIUM"
        return "LOW"


def get_risk_thresholds() -> RiskThresholds:
    return RiskThresholds(
        low=settings.RISK_THRESHOLDS_LOW,
        medium=settings.RISK_THRESHOLDS_MEDIUM,
        high=settings.RISK_THRESHOLDS_HIGH,
    )


def classify_risk(risk_probability: float) -> str:
    """Single source of truth for risk-level classification."""
    return get_risk_thresholds().classify(risk_probability)
