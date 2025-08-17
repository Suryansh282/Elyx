"""Turn scheduled events + state into WhatsApp-style message threads (natural)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random
import platform
import re

from ..nlg import NLGEngine
from ..profile2 import Person, MemberProfile
from ..state import BiomarkerState
from ..interventions import (
    default_interventions,
    weekly_adherence_probability,
    bernoulli,
)
from ..calendar2 import TravelPlan  # noqa: F401 (context)
from .voices import VOICES
from . import templates as TPL


# ------------------------------------------------------------------------------------
# Message model
# ------------------------------------------------------------------------------------

@dataclass
class Message:
    """A single chat message."""
    timestamp: datetime
    sender: str
    text: str
    attachments: Optional[List[str]] = None
    initiated_by_member: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def author(self) -> str:
        return self.sender

    def as_json(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "sender": self.sender,
            "text": self.text,
            "attachments": self.attachments or [],
            "initiated_by_member": self.initiated_by_member,
        }

    def as_whatsapp(self) -> str:
        """Portable WhatsApp-like timestamp."""
        dt = self.timestamp
        if platform.system() == "Windows":
            yy = dt.strftime("%y")
            hour12 = dt.hour % 12 or 12
            minute = dt.strftime("%M")
            ampm = dt.strftime("%p")
            ts = f"{dt.month}/{dt.day}/{yy}, {hour12}:{minute} {ampm}"
        else:
            ts = self.timestamp.strftime("%-m/%-d/%y, %-I:%M %p")
        return f"[{ts}] {self.sender}: {self.text}"


# ------------------------------------------------------------------------------------
# Conversation context
# ------------------------------------------------------------------------------------

@dataclass
class GenerationContext:
    """Holds evolving context across weeks for content realism."""
    last_week_win: bool = False
    cumulative_plan_hours: float = 0.0
    exercise_phase: int = 0  # increments every 2 weeks
    # remember the last opener we used per role (to reduce repetition)
    last_openers: Dict[str, str] = field(default_factory=dict)


# ------------------------------------------------------------------------------------
# Variation pools (to reduce repetition)
# ------------------------------------------------------------------------------------

# Wearable note variation
WEARABLE_BRIEFS = [
    "Night HRV dipped and RHR ticked up vs last week",
    "HRV was lower last night and resting HR ran higher",
    "Slight drop in HRV with a bump in resting heart rate",
    "Recovery looked a bit suppressed (lower HRV, higher RHR)",
]
WEARABLE_HYPO_TRAVEL = [
    "late meal plus the time-zone shift",
    "body clock mismatch from travel",
    "sleep timing plus a heavier dinner on arrival",
]
WEARABLE_HYPO_HOME = [
    "late caffeine with a stressful day",
    "under-recovery after back-to-back work days",
    "short sleep and evening coffee",
]
WEARABLE_NEXTS = [
    "earlier dinner, 10-min wind-down, and morning light tomorrow",
    "a morning walk in daylight and keep dinner earlier tonight",
    "10 minutes of breathing before bed and morning light exposure",
]

# Nutrition variation
NUTR_OBS_HOME = [
    "coffee keeps drifting past 1 pm and dinners are running late",
    "caffeine window is sliding and dinners have been later than ideal",
    "afternoon coffee shows up, and dinner timing’s a bit late",
]
NUTR_RECO_HOME = [
    "keep coffee to the morning, bring dinner earlier, and add two oily-fish meals this week",
    "tighten caffeine to mornings, eat dinner earlier, and include 2 fish meals",
    "morning-only coffee, earlier dinners, and hit two oily-fish meals this week",
]
NUTR_OBS_TRAVEL = [
    "restaurant meals look heavier on sodium and refined carbs",
    "hotel food has been saltier with more refined carbs",
]
NUTR_RECO_TRAVEL = [
    "ask for low-sodium prep, choose grilled fish + steamed greens, and skip late desserts",
    "request lighter seasoning, pick grilled proteins with greens, and avoid late desserts",
]

# Ruby weekly focus/action variation
FOCUS_CORE = [
    "morning light and earlier caffeine cutoff",
    "Zone-2 plus mobility consistency",
]
FOCUS_EXTRAS = [
    "earlier dinner on work-heavy days",
    "a 10-minute wind-down before bed",
    "hydration + electrolytes on travel days",
]
RUBY_ACTIONS = [
    "blocked your workout slots",
    "sent the updated menu brief to your home cook",
    "looped Sarah to confirm timings",
    "nudged the gym to hold a squat rack slot",
]

# Exercise cues variation
CUES_POOL = [
    "neutral spine and controlled eccentrics",
    "brace before you move; slow eccentrics",
    "tall posture, ribs down, smooth tempo",
]

# Casual confirmation variants
CONFIRM_VARIANTS = [
    "okay to proceed?",
    "want me to lock that in?",
    "good to go?",
    "sound okay?",
]


# ------------------------------------------------------------------------------------
# Content Engine
# ------------------------------------------------------------------------------------

class ContentEngine:
    """Convert events + state into natural messages and apply weekly effects."""

    def __init__(self, member: MemberProfile, team: List[Person], nlg: Optional[NLGEngine] = None):
        self.member = member
        self.team = {p.voice_key: p for p in team}
        self.interventions = default_interventions()
        self.ctx = GenerationContext()
        self.week_counter = 0
        self.nlg = nlg
        # recent (author, kind) -> timestamp to suppress near-duplicates
        self._recent: Dict[tuple[str, str], datetime] = {}

    # ----------------- helpers -----------------

    def _extract_opener(self, text: str, max_words: int = 4) -> str:
        """
        Return a simple opener: first 3–4 words (lowercased) from the first non-greeting line.
        """
        if not text:
            return ""
        for raw in (L.strip() for L in text.splitlines()):
            if not raw:
                continue
            if re.match(r"(?i)^(hi|hello|hey)\s+\w+[,\-–]?$", raw):
                continue
            s = raw.strip().strip("“”\"' ")
            words = re.findall(r"[A-Za-z0-9']+", s.lower())
            if not words:
                continue
            return " ".join(words[:max_words])
        return ""

    def _remember_opener(self, role_key: str, text: str) -> None:
        op = self._extract_opener(text)
        if op:
            self.ctx.last_openers[role_key] = op

    def _enhance(
        self,
        role_key: str,
        event: str,
        header: str,
        base_body: str,
        facts: Optional[Dict[str, str]] = None
    ) -> str:
        """Send through NLG if configured; BODY only is returned."""
        if self.nlg is None:
            return self._tidy(base_body)
        role = VOICES[role_key].tag.split(" (")[0]  # e.g., "Ruby"
        facts = dict(facts or {})
        avoid = self.ctx.last_openers.get(role_key, "")
        if avoid:
            facts["avoid_opening_like"] = avoid
        text = self.nlg.enhance(role=role, event=event, header=header, base_body=base_body, facts=facts)
        return self._tidy(text)

    def _voice(self, key: str) -> str:
        return VOICES[key].tag

    def _member(self) -> str:
        return VOICES["member"].tag

    def _style_hint(self) -> str:
        return random.choice([
            "warm & brief",
            "to-the-point",
            "casual but clear",
            "executive and concise",
            "friendly and practical",
            "matter-of-fact",
        ])

    def _emit(self, msg: Message, kind: str, window_hours: float = 12.0) -> List[Message]:
        """
        Suppress near-duplicate messages of the same (author, kind) inside a short window.
        Returns [] if dropped; [msg] if emitted.
        """
        key = (msg.sender, kind)
        last = self._recent.get(key)
        if last is not None:
            delta_h = (msg.timestamp - last).total_seconds() / 3600.0
            if delta_h < window_hours:
                return []
        self._recent[key] = msg.timestamp
        return [msg]

    def _tidy(self, s: str) -> str:
        """
        Light grammar/punct cleanup to reduce rough edges:
        - collapse multiple spaces
        - fix '?.' / '!.' and '..' to a single punctuation
        - ensure each line starts capitalized if alphabetic
        - normalize awkward phrases
        """
        if not s:
            return s
        txt = s.strip()

        # Normalize weird punctuation combos
        txt = re.sub(r"\?\.", "?", txt)
        txt = re.sub(r"\!\.", "!", txt)
        txt = re.sub(r"\.{2,}", ".", txt)
        txt = re.sub(r"\s{2,}", " ", txt)
        txt = re.sub(r"(?m)[:;]\s*$", ".", txt)

        # Normalize awkward phrasing
        txt = re.sub(r"(?i)put attention on\b", "focus on", txt)

        # Capitalize first letter of each line when appropriate
        def _cap(line: str) -> str:
            m = re.match(r"^(\s*)([a-z])", line)
            if m:
                pre, ch = m.group(1), m.group(2)
                return f"{pre}{ch.upper()}{line[m.end():]}"
            return line

        lines = [_cap(L) for L in txt.splitlines()]
        txt = "\n".join(lines).strip()
        return txt

    # ----------------- week lifecycle -----------------

    def begin_week(self, state: BiomarkerState, travel: bool, busy: bool) -> Dict[str, bool]:
        weekly_hours = sum(iv.time_cost_hours for iv in self.interventions)
        pa_support = True
        adherence_map: Dict[str, bool] = {}

        for iv in self.interventions:
            p = weekly_adherence_probability(
                base=iv.base_adherence,
                travel=travel,
                pa_support=pa_support,
                busy_week=busy,
                last_week_win=self.ctx.last_week_win,
                weekly_hours=weekly_hours,
            )
            did = bernoulli(p)
            adherence_map[iv.name] = did
            state.apply_intervention_effects(iv.effect_vector, did)

        if travel:
            state.apply_travel_penalty()

        state.add_noise()
        state.weekly_bounds()

        win_count = 0
        if state.hrv_ms > 40.0:
            win_count += 1
        if state.apob < 105.0:
            win_count += 1
        if state.systolic_bp < 134.0:
            win_count += 1
        self.ctx.last_week_win = win_count >= 2

        return adherence_map

    # ----------------- message builders -----------------

    def weekly_report(self, when: datetime, state: BiomarkerState) -> List[Message]:
        """Ruby’s weekly summary (natural) + hours mention occasionally."""
        wins: List[str] = []
        flags: List[str] = []

        snap = state.snapshot()
        if snap.get("ApoB", 999) < 100.0:
            wins.append(f"ApoB trending down ({snap['ApoB']})")
        if snap.get("HRV(ms)", 0) > 42:
            wins.append(f"HRV improved ({snap['HRV(ms)']} ms)")
        if snap.get("Sleep(h)", 0) >= 6.5:
            wins.append(f"Sleep avg {snap['Sleep(h)']} h")

        if snap.get("SBP", 0) >= 130 or snap.get("DBP", 0) >= 85:
            flags.append(f"BP still elevated ({snap['SBP']}/{snap['DBP']})")
        if snap.get("hsCRP", 0) >= 1.5:
            flags.append(f"hsCRP {snap['hsCRP']}")

        # Focus & actions vary week to week
        focus = list(FOCUS_CORE)
        focus += random.sample(FOCUS_EXTRAS, k=1)
        actions = random.sample(RUBY_ACTIONS, k=2)
        if random.random() < 0.35:
            extra_action = random.choice([a for a in RUBY_ACTIONS if a not in actions])
            actions.append(extra_action)

        # weekly hours (mention ~35% to avoid robotic feel)
        try:
            hours_done = state.sample_weekly_hours()
            hours_target = getattr(state, "weekly_hours_committed", 5.0)
        except Exception:
            val = random.gauss(5.0, 1.0)
            hours_done = round(max(2.0, min(7.0, val)), 1)
            hours_target = 5.0
            state.weekly_hours_completed = hours_done
            state.weekly_hours_committed = hours_target

        base_body = TPL.weekly_report_text(wins, flags, focus, actions, name="Rohan")
        if random.random() < 0.35:
            hours_line = (
                f"You logged ~{hours_done}h this week; target is {hours_target}h. "
                f"Let’s aim for ≥{hours_target}h next week."
            )
            base_body = base_body + "\n" + hours_line

        facts = {
            "wins": "; ".join(wins) if wins else "",
            "flags": "; ".join(flags) if flags else "",
            "focus": "; ".join(focus) if focus else "",
            "actions": "; ".join(actions) if actions else "",
            "ApoB": snap.get("ApoB"),
            "BP": f"{snap.get('SBP')}/{snap.get('DBP')}",
            "HRV": snap.get("HRV(ms)"),
            "Sleep(h)": snap.get("Sleep(h)"),
            "hours_completed": hours_done,
            "hours_target": hours_target,
            "style_hint": self._style_hint(),
        }
        body = self._enhance("ruby", "weekly_report", "Weekly report:", base_body, facts)
        msg = Message(when, self._voice("ruby"), body, meta={"kind": "weekly_report"})
        emitted = self._emit(msg, kind="weekly_report", window_hours=4.0)
        if emitted:
            self._remember_opener("ruby", body)
        return emitted

    def exercise_update(self, when: datetime, state: BiomarkerState) -> List[Message]:
        self.ctx.exercise_phase += 1
        phase = self.ctx.exercise_phase

        change = bool(bernoulli(0.5)) if hasattr(state, "rng") else (random.random() < 0.5)
        if change:
            plan_change = (
                f"move to phase {phase} with +1 set on compound lifts; keep RPE 7–8 "
                f"and switch to suitcase carries during travel if your back tightens"
            )
        else:
            plan_change = "keep the current progression for two more weeks and reassess"

        cues = random.choice(CUES_POOL)

        base_body = TPL.exercise_update_text(
            progress=f"Phase {max(0, phase-1)} went smoothly; no acute pain",
            plan_change=plan_change,
            cues=cues,
            name="Rohan",
        )
        facts = {
            "phase": phase,
            "RPE": "7–8",
            "plan_change": plan_change,
            "cues": cues,
            "style_hint": self._style_hint(),
        }
        body = self._enhance("rachel", "exercise_update", "Exercise update:", base_body, facts)
        msg = Message(when, self._voice("rachel"), body, meta={"kind": "exercise_update"})
        emitted = self._emit(msg, kind="exercise_update", window_hours=10.0)
        if emitted:
            self._remember_opener("rachel", body)
        if change and emitted:
            emitted[0].meta["plan_change"] = True
        return emitted

    def medical_checkin(self, when: datetime, state: BiomarkerState) -> List[Message]:
        # Light variation in plan wording
        plan_variants = [
            "stay the course for now; review at the next panel; hydrate and keep sodium balanced",
            "continue the current plan; we’ll review at the next panel; keep hydration and sodium steady",
            "no medication changes yet; revisit at the next panel; maintain hydration and sodium balance",
        ]
        plan = random.choice(plan_variants)
        base_body = TPL.medical_checkin_text(
            symptoms="occasional lightheadedness on long meetings; sleep latency a bit better",
            review=f"BP {state.systolic_bp:.0f}/{state.diastolic_bp:.0f}, ApoB {state.apob:.0f}, hsCRP {state.hs_crp:.2f}",
            plan=plan,
            name="Rohan",
        )
        facts = {
            "symptoms": "lightheadedness improving; better sleep latency",
            "review": f"{state.systolic_bp:.0f}/{state.diastolic_bp:.0f}, ApoB {state.apob:.0f}, hsCRP {state.hs_crp:.2f}",
            "ApoB": f"{state.apob:.0f}",
            "hsCRP": f"{state.hs_crp:.2f}",
            "style_hint": self._style_hint(),
        }
        body = self._enhance("dr_warren", "medical_checkin", "Medical check-in:", base_body, facts)
        msg = Message(when, self._voice("dr_warren"), body, meta={"kind": "medical_checkin"})
        emitted = self._emit(msg, kind="medical_checkin", window_hours=8.0)
        if emitted:
            self._remember_opener("dr_warren", body)
        return emitted

    def nutrition_update(self, when: datetime, traveling: bool) -> List[Message]:
        if traveling:
            observation = random.choice(NUTR_OBS_TRAVEL)
            recommendation = random.choice(NUTR_RECO_TRAVEL)
        else:
            observation = random.choice(NUTR_OBS_HOME)
            recommendation = random.choice(NUTR_RECO_HOME)

        base_body = TPL.nutrition_update_text(observation, recommendation, name="Rohan")
        facts = {
            "observation": observation,
            "recommendation": recommendation,
            "traveling": str(traveling),
            "style_hint": self._style_hint(),
        }
        body = self._enhance("carla", "nutrition_update", "Nutrition update:", base_body, facts)
        msg = Message(when, self._voice("carla"), body, meta={"kind": "nutrition_update"})
        emitted = self._emit(msg, kind="nutrition_update", window_hours=12.0)
        if emitted:
            self._remember_opener("carla", body)
        return emitted

    def travel_adaptation(self, when: datetime, dest: str) -> List[Message]:
        plan = (
            "on flight day, shift meal timing; get 10–15 min of morning light on arrival; "
            "use hotel-gym swaps (DB rows, goblet squats, carries); hydrate with electrolytes"
        )
        confirm = random.choice(CONFIRM_VARIANTS)
        base_body = TPL.travel_adaptation_text(dest, plan, name="Rohan")
        base_body = f"{base_body}\n{confirm.capitalize()}"
        facts = {
            "destination": dest,
            "plan": plan,
            "style_hint": self._style_hint(),
        }
        body = self._enhance("ruby", "travel_adaptation", "Travel adaptation", base_body, facts)
        msg = Message(when, self._voice("ruby"), body, meta={"kind": "travel_adaptation"})
        emitted = self._emit(msg, kind="travel_adaptation", window_hours=10.0)
        if emitted:
            self._remember_opener("ruby", body)
        return emitted

    def diagnostics_schedule(self, when: datetime) -> List[Message]:
        scope = (
            "OGTT+insulin, ApoB/ApoA, Lp(a), FBC, LFT/KFT, hsCRP/ESR, thyroid panel, hormones, "
            "micronutrients (incl. Omega-3), urinalysis, ECG/Echo/CIMT as indicated, DEXA"
        )
        base_body = TPL.diagnostics_schedule_text(scope, name="Rohan")
        facts = {
            "scope": scope,
            "style_hint": self._style_hint(),
        }
        body = self._enhance("ruby", "diagnostics_schedule", "Ordering your diagnostic panel", base_body, facts)
        msg = Message(when, self._voice("ruby"), body, meta={"kind": "diagnostics_schedule"})
        emitted = self._emit(msg, kind="diagnostics_schedule", window_hours=24.0)
        if emitted:
            self._remember_opener("ruby", body)
        return emitted

    def diagnostics_results(self, when: datetime, state: BiomarkerState) -> List[Message]:
        snap = state.snapshot()
        summary = f"ApoB {snap['ApoB']}, LDL {snap['LDL-C']}, BP {snap['SBP']}/{snap['DBP']}, hsCRP {snap['hsCRP']}"
        interpretation = "improving but still above targets for ApoB and BP; inflammation modestly better"
        options = [
            "continue lifestyle emphasis for 12 weeks",
            "discuss lipid-lowering therapy (pros/cons)",
            "tighten sodium and earlier caffeine cutoff",
        ]
        base_body = TPL.diagnostics_results_text(summary, interpretation, options, name="Rohan")
        facts = {
            "summary": summary,
            "interpretation": interpretation,
            "options": "; ".join(options),
            "ApoB": snap["ApoB"],
            "LDL": snap["LDL-C"],
            "BP": f"{snap['SBP']}/{snap['DBP']}",
            "hsCRP": snap["hsCRP"],
            "style_hint": self._style_hint(),
        }
        body = self._enhance("dr_warren", "diagnostics_results", "Diagnostics results", base_body, facts)
        msg = Message(when, self._voice("dr_warren"), body, meta={"kind": "diagnostics_results"})
        emitted = self._emit(msg, kind="diagnostics_results", window_hours=24.0)
        if emitted:
            self._remember_opener("dr_warren", body)
        return emitted

    def wearable_anomaly(self, when: datetime, state: BiomarkerState, travel: bool) -> List[Message]:
        brief = random.choice(WEARABLE_BRIEFS)
        hypothesis = random.choice(WEARABLE_HYPO_TRAVEL if travel else WEARABLE_HYPO_HOME)
        next_step = random.choice(WEARABLE_NEXTS)
        base_body = TPL.wearable_anomaly_text(brief, hypothesis, next_step, name="Rohan")
        facts = {
            "brief": brief,
            "hypothesis": hypothesis,
            "next": next_step,
            "HRV": f"{state.hrv_ms:.1f}",
            "RHR": f"{state.rhr_bpm:.1f}",
            "travel": str(travel),
            "style_hint": self._style_hint(),
        }
        body = self._enhance("advik", "wearable_anomaly", "Wearable note", base_body, facts)
        msg = Message(when, self._voice("advik"), body, meta={"kind": "wearable_anomaly"})
        emitted = self._emit(msg, kind="wearable_anomaly", window_hours=10.0)
        if emitted:
            self._remember_opener("advik", body)
        return emitted

    def member_curiosity(self, when: datetime) -> List[Message]:
        topics = [
            "ApoB vs LDL-C",
            "Creatine and cognition",
            "Jet lag meal timing",
            "Strength training and BP",
            "Fish oil purity standards",
            "Zone-2 heart-rate zones",
            "Mediterranean vs DASH diet",
        ]
        asks = [
            "Quick take?",
            "Worth trying?",
            "How does this apply to me?",
            "Any risk I should know?",
            "What’s the simplest version?",
        ]
        text = TPL.member_curiosity_text(random.choice(topics), random.choice(asks), name="Rohan")
        text = self._tidy(text)  # fix stray '?.' / spacing / capitalization
        msg = Message(when, self._member(), text, initiated_by_member=True, meta={"kind": "member_curiosity"})
        return self._emit(msg, kind="member_curiosity", window_hours=4.0)

    def pa_scheduling_ack(self, when: datetime) -> List[Message]:
        """Short PA (Sarah) confirmation message for scheduling/logistics."""
        try:
            sender = self._voice("pa")
        except KeyError:
            sender = self._voice("ruby")

        options = [
            "Calendar invites sent; lab location shared.",
            "Diagnostics confirmed; QR code is in your email.",
            "Travel holds added; workout times adjusted in your calendar.",
            "Reminder set and shared with Sarah.",
            "All set on my side. Shout if you need anything changed.",
        ]
        text = random.choice(options)
        msg = Message(when, sender, text, meta={"kind": "pa_ack"})
        return self._emit(msg, kind="pa_ack", window_hours=8.0)


def minutes_apart(ts: datetime, minutes: int) -> datetime:
    return ts + timedelta(minutes=minutes)
