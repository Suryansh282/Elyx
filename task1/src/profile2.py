"""Member and Elyx team profiles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Person:
    """Represents a person involved in the conversation."""
    name: str
    role: str
    voice_key: str  # used by content engine to select tone


@dataclass(frozen=True)
class MemberProfile:
    """Represents the member's immutable profile and preferences."""
    preferred_name: str
    dob: str
    age: int
    gender: str
    primary_residence: str
    frequent_travel: List[str]
    occupation: str
    pa_name: str
    goals: List[str]
    success_metrics: List[str]
    comm_pref: str
    language: str
    cultural_background: str


def get_member_profile() -> MemberProfile:
    """Return the fixed member profile for this simulation."""
    return MemberProfile(
        preferred_name="Rohan Patel",
        dob="1979-03-12",
        age=46,
        gender="Male",
        primary_residence="Singapore",
        frequent_travel=["United Kingdom", "United States", "South Korea", "Jakarta"],
        occupation="Regional Head of Sales (FinTech)",
        pa_name="Sarah Tan",
        goals=[
            "Reduce CVD risk via cholesterol/BP control by Dec 2026",
            "Enhance cognitive function & focus by Jun 2026",
            "Annual full-body screening cadence starting Nov 2025",
        ],
        success_metrics=[
            "ApoB, LDL-C, BP, hsCRP",
            "Sleep quality (Garmin), HRV, RHR",
            "Cognitive assessment scores",
        ],
        comm_pref=(
            "Executive summaries with clear actions; granular data on request. "
            "Scheduling via PA, responses within 24–48h."
        ),
        language="English",
        cultural_background="Indian",
    )


def get_elyx_team() -> List[Person]:
    """Return the fixed Elyx team with roles and voice selectors."""
    return [
        Person("Ruby", "Elyx Concierge (Orchestrator)", "ruby"),
        Person("Dr. Warren", "Elyx Medical Strategist", "dr_warren"),
        Person("Advik", "Elyx Performance Scientist", "advik"),
        Person("Carla", "Elyx Nutritionist", "carla"),
        Person("Rachel", "Elyx Physiotherapist", "rachel"),
        Person("Neel", "Elyx Concierge Lead / Relationship Manager", "neel"),
        Person("Sarah Tan", "Personal Assistant (Member)", "pa"),
        Person("Rohan Patel", "Member", "member"),
    ]
