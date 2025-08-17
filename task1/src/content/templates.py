"""Conversational templates (header-free). The generator calls the LLM with FULL mode,
so these are only used for paraphrase mode or as light seeds. They avoid labels/bullets,
reduce repetitive phrasing, clean punctuation, and dedupe duplicate lines."""
from __future__ import annotations

from typing import List
import random
import re

from ..textstyle import natural_list, to_sentence, map_actions, weave_report

# -------------------------
# Variation pools
# -------------------------

# Greeting chance for TEAM roles (0.0–1.0)
GREET_CHANCE = 0.18

ACKS = ["Got it.", "Understood.", "Noted.", "Okay."]
GREETS = ["Hi {name},", "Hey {name},", "Hello {name},"]

CONFIRMS = [
    "okay to proceed?",
    "want me to lock that in?",
    "good to go?",
    "sound okay?",
    "shall I confirm?",
]

OBS_LEADS = [
    "I noticed",
    "I'm seeing",
    "Looks like",
    "Your log shows",
    "Noticed",
    "From this week,",
]

TRY_LEADS = [
    "Let's try",
    "How about we",
    "Plan for this week:",
    "Let's go with",
    "Next up,",
]

MED_SYMPTOM_LEADS = [
    "I'm noting",
    "Noted",
    "From your update,",
    "On symptoms,",
]

MED_NUMS_LEADS = [
    "Current numbers are",
    "Latest numbers:",
    "On labs/vitals:",
]

MED_PLAN_LEADS = [
    "Let's stick with",
    "Plan:",
    "We'll continue with",
    "No changes —",
]

TRAVEL_LEADS = [
    "For {dest}, the plan is",
    "For {dest}, let's go with",
    "{dest}: plan is",
]

RESULTS_LEADS = [
    "Results are in —",
    "Got the results —",
    "Panel summary —",
]

INTERPRET_LEADS = [
    "This means",
    "My read:",
    "In short,",
]

OPTIONS_LEADS = [
    "Options include",
    "We can go a few ways:",
    "We could",
    "Paths:",
]

WEAR_HYP_LEADS = [
    "Likely",
    "Probably",
    "My hunch is",
    "Signals point to",
]

WEAR_NEXT_LEADS = [
    "Let's do",
    "Plan:",
    "Next:",
    "Try",
]


# -------------------------
# Helpers: greet, finalize, cleanup
# -------------------------

def _maybe_greet(name: str) -> str:
    return random.choice(GREETS).format(name=name) if random.random() < GREET_CHANCE else ""


def _normalize_for_dupe(line: str) -> str:
    # Lowercase, trim, strip trailing punctuation/spaces for dupe detection
    s = line.strip().lower()
    s = re.sub(r"[.?!…]+$", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _dedupe_lines(lines: List[str]) -> List[str]:
    seen = set()
    out = []
    for ln in lines:
        key = _normalize_for_dupe(ln)
        if key and key not in seen:
            seen.add(key)
            out.append(ln)
    return out


def _tidy_text(text: str) -> str:
    """Light grammar/punct cleanup across the whole block."""
    if not text:
        return text
    t = text.strip()

    # Normalize punctuation combos and spaces
    t = re.sub(r"\?\.", "?", t)
    t = re.sub(r"\!\.", "!", t)
    t = re.sub(r"\.{2,}", ".", t)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\s+([,.;!?])", r"\1", t)      # remove spaces before punctuation
    t = re.sub(r"([,;])([^\s])", r"\1 \2", t)  # ensure space after comma/semicolon

    # Turn dangling ':' or ';' at EOL into a period
    t = re.sub(r"(?m)[:;]\s*$", ".", t)

    # Capitalize first alpha of each line
    def _cap(line: str) -> str:
        m = re.match(r"^(\s*)([a-z])", line)
        if m:
            pre, ch = m.group(1), m.group(2)
            return f"{pre}{ch.upper()}{line[m.end():]}"
        return line

    lines = [_cap(L.strip()) for L in t.splitlines() if L.strip()]
    return "\n".join(lines).strip()


def _finalize(lines: List[str]) -> str:
    lines = [ln for ln in lines if ln and ln.strip()]
    lines = _dedupe_lines(lines)
    return _tidy_text("\n".join(lines))


# -------------------------
# Templates
# -------------------------

def weekly_report_text(
    wins: List[str],
    flags: List[str],
    focus: List[str],
    actions: List[str],
    name: str = "Rohan",
) -> str:
    """2–4 short sentences, no labels, no bullets. Varied confirmation phrase."""
    lines: List[str] = []
    g = _maybe_greet(name)
    if g:
        lines.append(g)

    # weave_report() returns short, human lines across wins/flags/focus
    lines += weave_report(wins, flags, focus)

    if actions:
        human = map_actions(actions)  # e.g., "I blocked your workout slots and sent the menu brief"
        confirm = random.choice(CONFIRMS)
        # Let to_sentence handle punctuation; we avoid double punctuation by finalizer
        lines.append(to_sentence(f"{human} — {confirm}"))
    else:
        lines.append("Nothing needed from you right now.")

    return _finalize(lines)


def exercise_update_text(
    progress: str,
    plan_change: str,
    cues: str,
    name: str = "Rohan",
) -> str:
    lines: List[str] = []
    g = _maybe_greet(name)
    if g:
        lines.append(g)

    lines.append(to_sentence(progress))  # sentence-first, no labels
    lines.append(to_sentence(f"For the next block, {plan_change}"))
    lines.append(to_sentence(f"Keep an eye on {cues}"))
    lines.append(random.choice(["Good to go?", "Sound okay?", "Comfortable with that?"]))
    return _finalize(lines)


def medical_checkin_text(
    symptoms: str,
    review: str,
    plan: str,
    name: str = "Rohan",
) -> str:
    lines: List[str] = []
    g = _maybe_greet(name)
    if g:
        lines.append(g)

    lines.append(to_sentence(f"{random.choice(MED_SYMPTOM_LEADS)} {symptoms}"))
    lines.append(to_sentence(f"{random.choice(MED_NUMS_LEADS)} {review}"))
    lines.append(to_sentence(f"{random.choice(MED_PLAN_LEADS)} {plan}"))
    return _finalize(lines)


def nutrition_update_text(
    observation: str,
    recommendation: str,
    name: str = "Rohan",
) -> str:
    lines: List[str] = []
    g = _maybe_greet(name)
    if g:
        lines.append(g)

    lines.append(to_sentence(f"{random.choice(OBS_LEADS)} {observation}"))
    # Ensure we don't always open with “Let's try …”
    lead = random.choice(TRY_LEADS)
    # If the lead ends with a colon, rely on finalizer to tidy end punctuation.
    lines.append(to_sentence(f"{lead} {recommendation}"))
    return _finalize(lines)


def travel_adaptation_text(
    dest: str,
    plan: str,
    name: str = "Rohan",
) -> str:
    lines: List[str] = []
    g = _maybe_greet(name)
    if g:
        lines.append(g)

    lead = random.choice(TRAVEL_LEADS).format(dest=dest)
    lines.append(to_sentence(f"{lead} {plan}"))
    return _finalize(lines)


def diagnostics_schedule_text(
    scope: str,
    name: str = "Rohan",
) -> str:
    lines: List[str] = []
    g = _maybe_greet(name)
    if g:
        lines.append(g)

    lines.append(to_sentence(f"I’m booking this panel — {scope}"))
    lines.append("Fasting instructions are in your inbox.")
    return _finalize(lines)


def diagnostics_results_text(
    summary: str,
    interpretation: str,
    options: List[str],
    name: str = "Rohan",
) -> str:
    lines: List[str] = []
    g = _maybe_greet(name)
    if g:
        lines.append(g)

    lines.append(to_sentence(f"{random.choice(RESULTS_LEADS)} {summary}"))
    lines.append(to_sentence(f"{random.choice(INTERPRET_LEADS)} {interpretation}"))
    if options:
        lines.append(to_sentence(f"{random.choice(OPTIONS_LEADS)} {natural_list(options, 'or')}"))
    return _finalize(lines)


def wearable_anomaly_text(
    brief: str,
    hypothesis: str,
    next_step: str,
    name: str = "Rohan",
) -> str:
    """Wearable note without labels; short WhatsApp-style sentences."""
    lines: List[str] = []
    g = _maybe_greet(name)
    if g:
        lines.append(g)

    lines.append(to_sentence(brief))  # e.g., "Night HRV dipped and RHR rose vs last week."
    lines.append(to_sentence(f"{random.choice(WEAR_HYP_LEADS)} {hypothesis}"))
    lines.append(to_sentence(f"{random.choice(WEAR_NEXT_LEADS)} {next_step}"))
    return _finalize(lines)


def member_curiosity_text(
    topic: str,
    ask: str,
    name: str = "Rohan",
) -> str:
    # More phrasings to reduce repetition
    variants = [
        f"Quick one: {ask} ({topic}).",
        f"Saw something on {topic} — {ask}.",
        f"{ask} — re {topic}.",
        f"Curious about {topic}. {ask}.",
        f"{ask} ({topic}).",
        f"Reading about {topic}. {ask}",
        f"Any quick context on {topic}? {ask}",
        f"{ask} on {topic}?",
    ]
    # Light punctuation variety
    line = random.choice(variants)
    # Remove any accidental double punctuation; capitalization handled upstream if needed
    line = re.sub(r"\.{2,}$", ".", line.strip())
    return line


def ack_text() -> str:
    return random.choice(ACKS)
