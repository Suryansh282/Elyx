"""Health state, wearables, and weekly update logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple
import random


@dataclass
class BiomarkerState:
    """
    Tracks biomarker and wearable metrics.

    Values are intentionally simple and updated weekly with:
    - small deterministic drifts from interventions (scaled by adherence)
    - negative modifiers during travel weeks
    - small gaussian noise for realism
    """
    # Biomarkers (units are indicative)
    systolic_bp: float = 134.0
    diastolic_bp: float = 86.0
    apob: float = 105.0
    ldl_c: float = 140.0
    hs_crp: float = 2.2
    hba1c: float = 5.7
    bmi: float = 26.0

    # Wearables
    hrv_ms: float = 40.0
    rhr_bpm: float = 66.0
    sleep_hours: float = 6.25  # nightly average

    # Internal accumulators
    week_index: int = 0
    adherence_log: Dict[str, bool] = field(default_factory=dict)

    # NEW: weekly commitment tracking (lightweight)
    weekly_hours_committed: float = 5.0
    weekly_hours_completed: float = field(default=0.0)

    def apply_intervention_effects(self, effect_vector: Dict[str, float], adhered: bool) -> None:
        """Apply weekly effect if the member adhered to the intervention."""
        if not adhered:
            return
        for key, delta in effect_vector.items():
            self._apply_delta(key, delta)

    def apply_travel_penalty(self) -> None:
        """
        Travel weeks reduce sleep and HRV, increase RHR slightly,
        and may worsen BP marginally.
        """
        self._apply_delta("sleep_hours", -0.20)
        self._apply_delta("hrv_ms", -1.0)
        self._apply_delta("rhr_bpm", +1.0)
        self._apply_delta("systolic_bp", +0.5)
        self._apply_delta("diastolic_bp", +0.3)

    def add_noise(self) -> None:
        """Add small Gaussian noise to avoid straight lines."""
        noise_spec: Dict[str, float] = {
            "systolic_bp": 0.4,
            "diastolic_bp": 0.3,
            "apob": 0.6,
            "ldl_c": 0.8,
            "hs_crp": 0.10,
            "hba1c": 0.02,
            "bmi": 0.03,
            "hrv_ms": 0.8,
            "rhr_bpm": 0.5,
            "sleep_hours": 0.10,
        }
        for key, sigma in noise_spec.items():
            jitter = random.gauss(0.0, sigma)
            self._apply_delta(key, jitter)

    def weekly_bounds(self) -> None:
        """Clamp values to plausible human ranges."""
        self.systolic_bp = min(max(self.systolic_bp, 95.0), 170.0)
        self.diastolic_bp = min(max(self.diastolic_bp, 55.0), 110.0)
        self.apob = min(max(self.apob, 50.0), 200.0)
        self.ldl_c = min(max(self.ldl_c, 40.0), 250.0)
        self.hs_crp = min(max(self.hs_crp, 0.2), 10.0)
        self.hba1c = min(max(self.hba1c, 4.8), 7.0)
        self.bmi = min(max(self.bmi, 18.0), 35.0)
        self.hrv_ms = min(max(self.hrv_ms, 20.0), 120.0)
        self.rhr_bpm = min(max(self.rhr_bpm, 45.0), 90.0)
        self.sleep_hours = min(max(self.sleep_hours, 4.0), 9.0)

    def snapshot(self) -> Dict[str, float]:
        """Return a dictionary snapshot of current metrics."""
        return {
            "SBP": round(self.systolic_bp, 1),
            "DBP": round(self.diastolic_bp, 1),
            "ApoB": round(self.apob, 1),
            "LDL-C": round(self.ldl_c, 1),
            "hsCRP": round(self.hs_crp, 2),
            "HbA1c": round(self.hba1c, 2),
            "BMI": round(self.bmi, 1),
            "HRV(ms)": round(self.hrv_ms, 1),
            "RHR(bpm)": round(self.rhr_bpm, 1),
            "Sleep(h)": round(self.sleep_hours, 2),
        }

    def _apply_delta(self, key: str, delta: float) -> None:
        """Helper to mutate a state attribute if it exists."""
        if hasattr(self, key):
            setattr(self, key, getattr(self, key) + delta)

    def sample_weekly_hours(self, rng: random.Random | None = None) -> float:
        """
        Sample completed hours around 5h with small variance and clamp to [2,7].
        Call this once per week before composing the weekly report.
        """
        r = rng or random
        val = r.gauss(5.0, 1.0)
        val = max(2.0, min(7.0, val))
        self.weekly_hours_completed = round(val, 1)
        return self.weekly_hours_completed