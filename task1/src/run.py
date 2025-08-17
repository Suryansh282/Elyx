"""CLI to run the end-to-end pipeline and generate the conversation."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List
import random
from .nlg import NLGEngine

from zoneinfo import ZoneInfo

from .profile2 import get_member_profile, get_elyx_team
from .calendar2 import SimClock, build_travel_plan
from .state import BiomarkerState
from .scheduler import build_events
from .content.generator import ContentEngine, Message, minutes_apart
from .validators import validate_conversation
from .export import export_jsonl, export_txt


@dataclass
class Args:
    seed: int
    start: str
    weeks: int
    tz: str
    output_dir: Path
    use_local_paraphrase: bool
    nlg_provider: str         
    nlg_mode: str             
    llm_model: str            


def parse_args() -> Args:
    parser = argparse.ArgumentParser(description="Generate Elyx WhatsApp-style conversation.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--start", type=str, default="2025-01-06", help="Start date (ISO: YYYY-MM-DD)")
    parser.add_argument("--weeks", type=int, default=34, help="Number of weeks (≈8 months)")
    parser.add_argument("--tz", type=str, default="Asia/Singapore", help="IANA timezone")
    parser.add_argument("--output_dir", type=str, default="./demo", help="Where to write outputs")
    parser.add_argument(
        "--use_local_paraphrase",
        type=lambda s: s.lower() == "true",
        default=False,
        help="(Optional) If you wire in a local LLM paraphraser, toggle here. Not required.",
    )
    parser.add_argument("--nlg_provider", type=str, default="none", help="none | ollama")
    parser.add_argument("--nlg_mode", type=str, default="paraphrase", help="off | paraphrase | full")
    parser.add_argument("--llm_model", type=str, default="phi3:mini", help="ollama model name, e.g., phi3:mini or llama3.1:8b")

    ns = parser.parse_args()
    return Args(
        seed=ns.seed,
        start=ns.start,
        weeks=ns.weeks,
        tz=ns.tz,
        output_dir=Path(ns.output_dir),
        use_local_paraphrase=ns.use_local_paraphrase,
        nlg_provider=ns.nlg_provider,     
        nlg_mode=ns.nlg_mode,             
        llm_model=ns.llm_model,           
    )


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    # Setup
    tz = ZoneInfo(args.tz)
    start_dt = datetime.fromisoformat(args.start).replace(tzinfo=tz)
    clock = SimClock(start_date=start_dt, tz=tz)

    member = get_member_profile()
    team = get_elyx_team()
    travel_plan = build_travel_plan(weeks=args.weeks)
    nlg_engine = NLGEngine.from_args(
        provider=args.nlg_provider, mode=args.nlg_mode, model=args.llm_model
    )
    engine = ContentEngine(member=member, team=team, nlg=nlg_engine)

    state = BiomarkerState()
    events = build_events(clock, member, travel_plan, total_weeks=args.weeks)

    messages: List[Message] = []

    # Iterate by week, apply state updates, then render events into messages
    current_week = 1
    for ev in events:
        # When a new week starts, update state & adherence
        if ev.week != current_week:
            current_week = ev.week

        # Determine contextual flags
        traveling = travel_plan.destination_for_week(ev.week) is not None
        busy = (ev.week % 6 == 0)  # rough: every ~6 weeks is "busy board prep" week

        # Begin-week updates exactly once per week: we trigger when Monday 8–12am window events occur first
        # Simple approach: if it's Monday and morning, assume start-of-week update
        if ev.when.weekday() == 0 and 8 <= ev.when.hour <= 12:
            engine.begin_week(state, travel=traveling, busy=busy)

        # Route event to content builders
        if ev.kind == "weekly_report":
            messages += engine.weekly_report(ev.when, state)
        elif ev.kind == "exercise_update":
            messages += engine.exercise_update(ev.when, state)
        elif ev.kind == "medical_checkin":
            messages += engine.medical_checkin(ev.when, state)
        elif ev.kind == "nutrition_update":
            messages += engine.nutrition_update(ev.when, traveling)
        elif ev.kind == "travel_adaptation":
            messages += engine.travel_adaptation(ev.when, ev.meta.get("dest", ""))
        elif ev.kind == "diagnostics_schedule":
            messages += engine.diagnostics_schedule(ev.when)
            # PA confirmation shortly after
            messages += engine.pa_scheduling_ack(minutes_apart(ev.when, 20))
        elif ev.kind == "diagnostics_results":
            messages += engine.diagnostics_results(ev.when, state)
        elif ev.kind == "wearable_anomaly":
            messages += engine.wearable_anomaly(ev.when, state, travel=traveling)
        elif ev.kind == "member_curiosity":
            # Member asks; then a relevant expert replies ~15 min later
            m0 = engine.member_curiosity(ev.when)
            messages += m0
            reply_time = minutes_apart(ev.when, 15)
            # Route to likely expert
            reply = random.choice(
                [
                    engine.nutrition_update(reply_time, traveling),
                    engine.medical_checkin(reply_time, state),
                    engine.wearable_anomaly(reply_time, state, travel=traveling),
                ]
            )
            messages += reply

    # Validate
    validate_conversation(messages, total_weeks=args.weeks)

    # Export
    out_json = args.output_dir / "conversation.jsonl"
    out_txt = args.output_dir / "conversation.txt"
    export_jsonl(messages, out_json)
    export_txt(messages, out_txt)

    print(f"Wrote {out_json}")
    print(f"Wrote {out_txt}")


if __name__ == "__main__":
    main()
