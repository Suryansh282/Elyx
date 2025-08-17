"""Calendar and travel scheduling utilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional


@dataclass(frozen=True)
class SimClock:
    """Simulation clock based on a start date and timezone."""
    start_date: datetime
    tz: ZoneInfo

    def datetime_for(self, week: int, day_offset: int = 0, hour: int = 9, minute: int = 0) -> datetime:
        """
        Produce a timezone-aware datetime for a given week and offset.

        week: 1-based week index
        day_offset: days after the week's Monday (0..6)
        """
        base_monday = self.start_date + timedelta(weeks=week - 1)
        dt = datetime(
            year=base_monday.year,
            month=base_monday.month,
            day=base_monday.day,
            hour=hour,
            minute=minute,
            tzinfo=self.tz,
        ) + timedelta(days=day_offset)
        return dt


@dataclass
class TravelPlan:
    """Represents where the member is traveling on specific weeks."""
    travel_weeks: List[int]
    destinations: List[str]

    def destination_for_week(self, week: int) -> Optional[str]:
        """Return the destination if the given week is a travel week."""
        if week in self.travel_weeks:
            idx = self.travel_weeks.index(week) % len(self.destinations)
            return self.destinations[idx]
        return None


def build_travel_plan(weeks: int) -> TravelPlan:
    """
    Create a simple travel plan: at least 1 travel week out of every 4 weeks.

    We select weeks 4, 8, 12, 16, 20, 24, 28, 32 by default.
    """
    travel_weeks = []
    for w in range(4, weeks + 1, 4):
        travel_weeks.append(w)
    destinations = ["United Kingdom", "United States", "South Korea", "Jakarta"]
    return TravelPlan(travel_weeks=travel_weeks, destinations=destinations)
