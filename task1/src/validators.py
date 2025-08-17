"""Validators to guarantee hackathon constraints."""
from __future__ import annotations

from typing import List
from collections import Counter

from .content.generator import Message


def _diagnostic_weeks(total_weeks: int) -> list[int]:
    """
    Diagnostics cadence:
    - Baseline at week 4
    - Then every 12 weeks thereafter (16, 28, ...)
    """
    weeks = []
    w = 4
    while w <= total_weeks:
        weeks.append(w)
        w += 12
    return weeks


def _expected_diagnostics_count(total_weeks: int) -> int:
    """Number of diagnostics result summaries expected for the simulated span."""
    return len(_diagnostic_weeks(total_weeks))


def _count_kind_from_text(text_lower: str, kinds: Counter) -> None:
    """
    Backward-compatible heuristic counters based on leading text.
    Only used if meta['kind'] is absent.
    """
    if (
        text_lower.startswith("weekly report")
        or text_lower.startswith("wins")
        or text_lower.startswith("good signs")
        or text_lower.startswith("progress")
    ):
        kinds["weekly_report"] += 1
    if text_lower.startswith("exercise update"):
        kinds["exercise_update"] += 1
    if text_lower.startswith("medical check-in"):
        kinds["medical_checkin"] += 1
    if text_lower.startswith("nutrition update"):
        kinds["nutrition_update"] += 1
    if text_lower.startswith("travel adaptation"):
        kinds["travel_adaptation"] += 1
    if text_lower.startswith("ordering your diagnostic panel"):
        kinds["diagnostics_schedule"] += 1
    if text_lower.startswith("diagnostics results"):
        kinds["diagnostics_results"] += 1
    if text_lower.startswith("wearable note"):
        kinds["wearable_anomaly"] += 1


def validate_conversation(messages: List[Message], total_weeks: int) -> None:
    """
    Raise AssertionError if any constraint is not met.
    - Weekly reports: >= total_weeks
    - Exercise updates: ~ every 2 weeks (>= total_weeks//2 - 1)
    - Diagnostics results: dynamic based on total_weeks (wk4, then +12w cadence)
    - Travel adaptations: >= total_weeks // 4
    - Member-initiated messages: ~5 per week average (allow band)
    """
    kinds = Counter()
    member_initiated = 0

    for m in messages:
        # 1) Prefer explicit kind tagging from generator meta
        k = None
        try:
            if isinstance(m.meta, dict):
                k = m.meta.get("kind")
        except Exception:
            k = None

        if k:
            kinds[k] += 1
        else:
            # 2) Fallback to legacy text-prefix heuristics
            text_lower = (m.text or "").strip().lower()
            _count_kind_from_text(text_lower, kinds)

        if getattr(m, "initiated_by_member", False):
            member_initiated += 1

    # Weekly reports
    assert kinds["weekly_report"] >= total_weeks, "Weekly reports missing."

    # Exercise updates
    assert kinds["exercise_update"] >= (total_weeks // 2 - 1), "Exercise updates too few."

    # Diagnostics (dynamic expectation based on simulated weeks)
    expected_diag = _expected_diagnostics_count(total_weeks)
    assert kinds["diagnostics_results"] == expected_diag, (
        f"Expected {expected_diag} diagnostics result summaries, "
        f"found {kinds['diagnostics_results']}."
    )

    # Travel adaptations
    assert kinds["travel_adaptation"] >= (total_weeks // 4), "Travel adaptations too few."

    # Member-initiated messages average ~5/week within a band
    avg_member = member_initiated / total_weeks if total_weeks > 0 else 0.0
    assert 3.0 <= avg_member <= 7.0, f"Member-initiated average out of band: {avg_member:.2f}"
