"""Role-specific voice helpers (style and phrasing)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Voice:
    """Lightweight voice profile for each role."""
    tag: str          # e.g., "Ruby (Elyx Concierge)"
    tone: str         # human description, not used programmatically
    signature: str    # optional closing or marker


VOICES = {
    "ruby": Voice(
        tag="Ruby (Elyx Concierge)",
        tone="Empathetic, organized, proactive",
        signature="",
    ),
    "dr_warren": Voice(
        tag="Dr. Warren (Elyx Medical)",
        tone="Authoritative, precise, scientific",
        signature="",
    ),
    "advik": Voice(
        tag="Advik (Elyx Performance Scientist)",
        tone="Analytical, hypothesis-driven",
        signature="",
    ),
    "carla": Voice(
        tag="Carla (Elyx Nutrition)",
        tone="Practical, behavioral, educational",
        signature="",
    ),
    "rachel": Voice(
        tag="Rachel (Elyx PT)",
        tone="Direct, encouraging, form & function",
        signature="",
    ),
    "neel": Voice(
        tag="Neel (Elyx Concierge Lead)",
        tone="Strategic, reassuring, big-picture",
        signature="",
    ),
    "pa": Voice(
        tag="Sarah Tan (PA)",
        tone="Efficient, scheduling-focused",
        signature="",
    ),
    "member": Voice(
        tag="Rohan",
        tone="Analytical, concise",
        signature="",
    ),
}
