"""Lightweight text helpers to make messages feel human (no labels, casual, non-repetitive)."""

from __future__ import annotations
from typing import Iterable, List
import random
import re


# -----------------------------
# List helper
# -----------------------------

def natural_list(items: Iterable[str], conj: str = "and") -> str:
    items = [i.strip() for i in items if i and i.strip()]
    n = len(items)
    if n == 0:
        return ""
    if n == 1:
        return items[0]
    if n == 2:
        return f"{items[0]} {conj} {items[1]}"
    return f"{', '.join(items[:-1])}, {conj} {items[-1]}"


# -----------------------------
# Sentence helpers (no labely prefixes; clean punctuation)
# -----------------------------

_END_BANG_Q_DOT = re.compile(r"([?!])\s*\.$")

def _trim_labely_bits(s: str) -> str:
    """
    Remove label-like phrases with trailing colons INSIDE a line:
      e.g., 'keeping an eye on: BP' -> 'keeping an eye on BP'
            'on labs/vitals: BP 130/84' -> 'on labs/vitals BP 130/84'
            'plan:' / 'next:' / 'summary:' -> removed
    """
    s = re.sub(
        r"(?i)\b("
        r"keeping an eye on|watch[-\s]?outs|flags|risks?|"
        r"plan|next|summary|interpretation|options|"
        r"on labs/vitals|on symptoms"
        r")\s*:\s*",
        r"\1 ",
        s,
    )
    return s

def to_sentence(s: str) -> str:
    """
    Normalize into a single clean sentence:
      - strip outer whitespace
      - remove internal colon labels
      - ensure exactly one terminal mark (., ?, or !)
      - never produce '?.' or '!.'
    """
    if not s:
        return ""
    t = s.strip().strip('"\''"“”‘’ ")
    t = _trim_labely_bits(t)

    # collapse spaces
    t = re.sub(r"\s{2,}", " ", t)

    # decide terminal punctuation
    end = "."
    if t.endswith(("?", "!", ".")):
        end = t[-1]
        t = t[:-1].rstrip()

    out = f"{t}{end}"
    out = out.replace("?.", "?").replace("!.", "!")
    out = _END_BANG_Q_DOT.sub(r"\1", out)
    return out


# -----------------------------
# Actions → one clean human sentence
# -----------------------------

def _normalize_action(a: str) -> str:
    """Remove leading 'I ' and trailing punctuation so we can join smoothly."""
    s = (a or "").strip()
    # common canned variants -> keep as-is if already clean
    s = re.sub(r"(?i)^\s*i\s+", "", s)       # drop leading "I "
    s = re.sub(r"\s*\.\s*$", "", s)          # drop trailing period
    return s

def map_actions(actions: List[str]) -> str:
    """
    Turn action fragments into a single natural sentence without labels.
    Example outputs:
      - "I blocked your workout slots."
      - "I blocked your workout slots and sent the updated menu brief to your home cook."
      - "I blocked your workout slots, looped Sarah to confirm timings, and nudged the gym to hold a squat rack slot."
    """
    if not actions:
        return "No actions from me right now"
    bits = [_normalize_action(a) for a in actions if a and a.strip()]
    if not bits:
        return "No actions from me right now"
    joined = natural_list(bits, "and")
    return f"I {joined}"


# -----------------------------
# Micro-variation for report lines (no colons)
# -----------------------------

_POS_TEMPLATES = [
    "Good news—{wins}",
    "Quick positive—{wins}",
    "On the plus side—{wins}",
    "Nice win—{wins}",
]

_FLAG_TEMPLATES = [
    "Still watching {flags}",
    "One thing to watch—{flags}",
    "Worth flagging—{flags}",
    "Still a risk—{flags}",
]

_FOCUS_TEMPLATES = [
    "This week let’s focus on {focus}",
    "For this week, let’s target {focus}",
    "Next week, keep attention on {focus}",
    "Let’s prioritize {focus}",
]

def _pick(template_list: List[str]) -> str:
    return random.choice(template_list)

def _merge_short_lines(parts: List[str]) -> List[str]:
    """Join very short fragments so the chat doesn’t feel bullet-y."""
    out: List[str] = []
    buf: List[str] = []
    for p in parts:
        if len(p) < 28:
            buf.append(p)
        else:
            if buf:
                out.append(" ".join(buf))
                buf = []
            out.append(p)
    if buf:
        out.append(" ".join(buf))
    return out


# -----------------------------
# Weave report (no labels, casual tone, low repetition)
# -----------------------------

def weave_report(wins: List[str], flags: List[str], focus: List[str]) -> List[str]:
    """
    Produce 2–3 compact, label-free sentences from wins/flags/focus.
    No headings, no colons, casual WhatsApp tone.
    """
    lines: List[str] = []

    # Wins
    if wins:
        w = natural_list(wins, "and")
        lines.append(to_sentence(_pick(_POS_TEMPLATES).format(wins=w)))
    else:
        lines.append(to_sentence("No big wins this week"))

    # Flags
    if flags:
        f = natural_list(flags, "and")
        lines.append(to_sentence(_pick(_FLAG_TEMPLATES).format(flags=f)))

    # Focus
    if focus:
        fo = natural_list(focus, "and")
        lines.append(to_sentence(_pick(_FOCUS_TEMPLATES).format(focus=fo)))

    # Compact if we created multiple short lines
    return _merge_short_lines(lines)
