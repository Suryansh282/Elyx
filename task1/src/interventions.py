"""Interventions and adherence model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import random


@dataclass(frozen=True)
class Intervention:
    """
    A weekly intervention with effect vectors on the BiomarkerState.

    effect_vector: per-week change when adhered (e.g., {"apob": -0.8})
    time_cost_hours: used to modulate adherence when plan > 5h/week
    recommended_by: which Elyx role proposes it
    """
    name: str
    domain: str
    effect_vector: Dict[str, float]
    time_cost_hours: float
    recommended_by: str
    base_adherence: float = 0.50  # baseline 50%


def default_interventions() -> List[Intervention]:
    """Return a canonical set of interventions used in the simulation."""
    return [
        Intervention(
            name="Mediterranean-pattern meals; reduce refined carbs",
            domain="Nutrition",
            effect_vector={"apob": -0.7, "ldl_c": -0.9, "hs_crp": -0.06, "bmi": -0.03},
            time_cost_hours=1.5,
            recommended_by="Carla",
        ),
        Intervention(
            name="Omega-3 (EPA/DHA) supplementation",
            domain="Nutrition",
            effect_vector={"apob": -0.4, "hs_crp": -0.05},
            time_cost_hours=0.1,
            recommended_by="Carla",
        ),
        Intervention(
            name="Caffeine cutoff at 13:00",
            domain="Sleep",
            effect_vector={"sleep_hours": +0.10, "hrv_ms": +0.5, "rhr_bpm": -0.2},
            time_cost_hours=0.0,
            recommended_by="Carla",
        ),
        Intervention(
            name="Morning light exposure (10–15 min)",
            domain="Sleep/Stress",
            effect_vector={"sleep_hours": +0.08, "hrv_ms": +0.6, "rhr_bpm": -0.2},
            time_cost_hours=0.3,
            recommended_by="Advik",
        ),
        Intervention(
            name="Zone-2 calibration run (1×/wk)",
            domain="Cardio",
            effect_vector={"hrv_ms": +0.7, "rhr_bpm": -0.3, "systolic_bp": -0.6, "diastolic_bp": -0.4},
            time_cost_hours=0.8,
            recommended_by="Advik",
        ),
        Intervention(
            name="Strength training (2×/wk) + daily 10-min mobility",
            domain="PT",
            effect_vector={"bmi": -0.04, "systolic_bp": -0.5, "diastolic_bp": -0.3},
            time_cost_hours=2.2,
            recommended_by="Rachel",
        ),
        Intervention(
            name="Sodium awareness (restaurant swaps when traveling)",
            domain="Nutrition/Travel",
            effect_vector={"systolic_bp": -0.4, "diastolic_bp": -0.3},
            time_cost_hours=0.2,
            recommended_by="Carla",
        ),
    ]


def weekly_adherence_probability(
    base: float,
    travel: bool,
    pa_support: bool,
    busy_week: bool,
    last_week_win: bool,
    weekly_hours: float,
) -> float:
    """
    Compute adherence probability modifiers.

    - Travel: -0.15
    - Busy week: -0.10
    - PA support: +0.10
    - Last week had "win": +0.05
    - Over-hours penalty (if weekly > 5h): -0.10
    """
    p = base
    if travel:
        p -= 0.15
    if busy_week:
        p -= 0.10
    if pa_support:
        p += 0.10
    if last_week_win:
        p += 0.05
    if weekly_hours > 5.0:
        p -= 0.10
    return max(0.05, min(0.95, p))


def bernoulli(p: float) -> bool:
    """Sample a Bernoulli outcome with probability p."""
    return random.random() < p
