"""Event scheduler for weekly/biweekly beats and member-initiated chats."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import random

from .calendar2 import SimClock, TravelPlan
from .profile2 import MemberProfile


# ---- Event Model -----------------------------------------------------------------


@dataclass(frozen=True)
class Event:
    """Base event: something that triggers one or more messages."""
    kind: str
    week: int
    when: datetime
    meta: Optional[dict] = None


def _random_time(base: datetime, hour_low: int = 8, hour_high: int = 20) -> datetime:
    """Return a datetime on the same date with a random hour/minute."""
    hour = random.randint(hour_low, hour_high)
    minute = random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    return base.replace(hour=hour, minute=minute)


# ---- Schedule Generation ----------------------------------------------------------


def build_events(
    clock: SimClock,
    profile: MemberProfile,
    travel: TravelPlan,
    total_weeks: int,
) -> List[Event]:
    """
    Emit a list of events (weekly reports, exercise updates, diagnostics, etc.)
    spanning total_weeks. This does not include state updates; it only schedules triggers.
    """
    events: List[Event] = []

    # Diagnostics (baseline at wk4; then wk16, wk28)
    diagnostic_weeks = [4, 16, 28]

    for w in range(1, total_weeks + 1):
        monday_9am = clock.datetime_for(week=w, day_offset=0, hour=9, minute=0)

        # Weekly report (Ruby)
        events.append(Event(kind="weekly_report", week=w, when=_random_time(monday_9am)))

        # Biweekly exercise update (Rachel)
        if w % 2 == 0:
            events.append(Event(kind="exercise_update", week=w, when=_random_time(monday_9am)))

        # Fortnightly medical check-in (Dr. Warren)
        if w % 2 == 0:
            events.append(Event(kind="medical_checkin", week=w, when=_random_time(monday_9am, 10, 14)))

        # Nutrition update roughly monthly (Carla)
        if w in {3, 7, 11, 15, 19, 23, 27, 31}:
            events.append(Event(kind="nutrition_update", week=w, when=_random_time(monday_9am, 11, 16)))

        # Travel week adaptations
        dest = travel.destination_for_week(w)
        if dest:
            events.append(
                Event(kind="travel_adaptation", week=w, when=_random_time(monday_9am), meta={"dest": dest})
            )

        # Diagnostics scheduling and results sharing
        if w in diagnostic_weeks:
            # Order / prep early in the week
            events.append(Event(kind="diagnostics_schedule", week=w, when=_random_time(monday_9am, 8, 11)))
            # Share results later in the week
            friday = monday_9am + timedelta(days=4)
            events.append(Event(kind="diagnostics_results", week=w, when=_random_time(friday, 13, 18)))

        # Member curiosity chats (~5 per week on average, cap 2 per day)
        # Simple distribution around 5 (3..7)
        weekly_count = random.randint(3, 7)
        for i in range(weekly_count):
            day = random.randint(0, 6)
            events.append(
                Event(kind="member_curiosity", week=w, when=_random_time(monday_9am + timedelta(days=day)))
            )

        # Wearable anomalies randomly (about once every 2 weeks)
        if random.random() < 0.5:
            day = random.randint(1, 6)
            events.append(
                Event(kind="wearable_anomaly", week=w, when=_random_time(monday_9am + timedelta(days=day)))
            )

    # Sort by datetime
    events.sort(key=lambda e: e.when)
    return events
