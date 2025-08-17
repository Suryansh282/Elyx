# Elyx Conversation Simulator

A no-cost, constraint-aware generator that produces 8 months of WhatsApp-style
conversations between **Rohan Patel** (Singapore) and the fixed **Elyx team**:
Ruby, Dr. Warren, Advik, Carla, Rachel, and Neel.

## Highlights

- Quarterly diagnostics (every ~12 weeks) with Dr. Warren interpretations
- ~5 member-initiated conversations/week (on average)
- Weekly report (Ruby), biweekly exercise updates (Rachel)
- Frequent travel (≥ 1 week out of every 4)
- ~50% adherence to interventions with data-driven plan changes
- Distinct voice & role for each Elyx member
- Exports to `.jsonl` and WhatsApp-like `.txt`

## Requirements

- Python 3.10+ (standard library only; zero paid APIs or extra packages)

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python src/run.py \
  --seed 42 \
  --start 2025-01-06 \
  --weeks 34 \
  --tz Asia/Singapore \
  --output_dir ./demo \
  --use_local_paraphrase false
