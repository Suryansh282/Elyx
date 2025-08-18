# Elyx Conversation Generator

Generate long, natural, WhatsApp-style conversations between a member and the Elyx team (Ruby the concierge, Dr. Warren, Carla in nutrition, Rachel in PT, and Advik on performance). The pipeline advances health state week-by-week, triggers events (weekly summaries, PT updates, diagnostics, travel, nutrition), and writes short, human messages with minimal repetition.

---

## Features

- **Multi-week simulation**: adherence, travel effects, random noise, and realistic “stay the course” vs. changes.
- **WhatsApp-like chat**: concise, label-free lines (no bullets or “Watch-outs:” prefixes).
- **Anti-repetition**
  - Variation pools for phrasing.  
  - Memory of each role’s last opener to avoid repeated starts.  
  - Post-processing that dedupes near-duplicate lines and fixes punctuation.
- **Local NLG (optional)**: Uses **Ollama + Llama-3.1** to paraphrase or compose messages from facts for a more natural tone.

---

## Project Structure

```
src/
├─ content/
│  ├─ generator.py       # Orchestrates weekly simulation and message building
│  ├─ templates.py       # Seed sentence builders (no labels)
│  ├─ textstyle.py       # Helpers: to_sentence, natural_list, weave_report
│  └─ voices.py          # Voice tags shown in the chat output
├─ nlg.py                # Local NLG polish (Ollama / Llama-3.1), prompts + cleanup
├─ profile2.py           # Member & team data models
├─ interventions.py      # Interventions, adherence model (Bernoulli), effects
├─ state.py              # BiomarkerState: HRV, BP, ApoB, hsCRP, Sleep
├─ calendar2.py          # Travel events (used as context)
└─ run.py                # CLI entrypoint to simulate & export conversations
```

---

## Architecture

### `src/content/generator.py` (orchestrator)
- Advances weekly state (applies interventions, travel effects, noise).
- Composes messages for events (weekly report, PT update, medical check-in, diagnostics, travel, nutrition, wearables).
- Uses **variation pools** + **last-opener memory** to reduce repetitive starts.
- Calls `templates.py` for clean seed sentences, then `nlg.py` to polish tone.
- Dedupes near-identical messages and outputs WhatsApp-style lines.

### `src/content/templates.py` (seed builders, no labels)
- Tiny sentence constructors like `weekly_report_text`, `medical_checkin_text`, `nutrition_update_text`, etc.
- Keeps language short and human; no bullets; no label-y prefixes.
- Relies on `textstyle.py` helpers (`to_sentence`, `natural_list`, `weave_report`).

### `src/content/textstyle.py` (helpers)
- Converts fragments to clean sentences, joins human lists, and weaves short report lines without labels.

### `src/nlg.py` (local NLG polish with Ollama)
- **Modes**:
  - `paraphrase` — rewrite the seed in a WhatsApp tone.
  - `full` — compose entirely from facts (least templated).
- Sends **role + event + facts** to **Ollama (Llama-3.1)** with role-specific tone + style hints.
- Respects `avoid_opening_like` (from generator memory) to vary openers.
- **Post-processing**: strips labels and role echoes, fixes punctuation/spacing, removes duplicate lines.

### `src/run.py`
- CLI entrypoint that wires everything together and writes output files.

---

## How It Works (Flow)

1. **Simulate the week**  
   `generator.begin_week()` draws adherence (Bernoulli), applies travel penalties, adds noise, and bounds biomarkers (BP, HRV, ApoB, hsCRP, Sleep). Context tracks “win” weeks and exercise phase.

2. **Create event messages**  
   For each scheduled event, `generator`:
   - Builds a **seed** via `templates.py` (short, casual, label-free).
   - Gathers **facts** (numbers, flags, actions, focus).
   - Adds `avoid_opening_like` with the role’s **last opener** to discourage repeats.

3. **Polish with NLG (optional)**  
   `nlg.py` (Ollama) paraphrases or composes from facts, then sanitizes and dedupes output.

4. **Render output**  
   Messages appear as:
   ```
   [m/d/yy, h:mm AM/PM] Sender: text
   ```
   and are written to your output directory (`conversation.txt` and/or JSON).

---

## Installation

> Requires **Python 3.10+**. Local NLG uses **Ollama** and the **Llama-3.1** model.

```bash
git clone <your-repo>
cd elyx-sim
python -m venv envElyx
# macOS/Linux
source envElyx/bin/activate
# Windows (PowerShell)
# .\envElyx\Scripts\Activate.ps1

pip install -r requirements.txt
```

**(Optional) Install Ollama + model**
```bash
# Install from https://ollama.com
ollama pull llama3.1:8b
# Ensure the service is running (defaults to http://localhost:11434)
```

---

## Usage

### A) With local NLG (most natural)
```bash
python -m src.run   --seed 42   --weeks 8   --tz Asia/Singapore   --output_dir ./demo   --nlg_provider ollama   --nlg_mode full   --llm_model llama3.1:8b
```

### B) Without NLG (faster, more templated)
```bash
python -m src.run   --seed 42   --weeks 8   --tz Asia/Singapore   --output_dir ./demo   --nlg_provider none   --nlg_mode off
```

**Useful flags**
- `--seed` — deterministic randomness for a run.  
- `--weeks` — conversation duration.  
- `--tz` — display timezone (e.g., `Asia/Singapore`).  
- `--output_dir` — where `conversation.txt/json` are written.  
- `--nlg_provider` — `ollama` or `none`.  
- `--nlg_mode` — `paraphrase`, `full`, or `off`.  
- `--llm_model` — e.g., `llama3.1:8b`.

> Tip: `--nlg_mode full` gives the least-templated feel. Keep `enable_cache=False` in `nlg.py` for variety.

---

## Example Output (Style)

```text
[1/27/25, 10:45 AM] Ruby (Elyx Concierge): I booked your panel—OGTT+insulin, ApoB/ApoA, Lp(a), and the rest. Fasting instructions are in your inbox.
[1/27/25, 11:05 AM] Sarah Tan (PA): Calendar invites sent; lab location shared.
[1/27/25, 2:20 PM] Dr. Warren (Elyx Medical): Noted lightheadedness improving. Right now: BP 132/84, ApoB 101, hsCRP 1.64. Let’s stay the course and recheck at the next panel.
```

Short, label-free, human tone.

---

## Configuration Knobs

- **`nlg.py` → `NLGConfig`**
  - `temperature`, `top_p`, `num_predict` — light sampling jitter per call.
  - `timeout_sec` — LLM call timeout.
  - `enable_cache` — keep **False** so each run differs.

- **`generator.py`**
  - Variation pools for wearables, nutrition, actions, confirmations.
  - Last-opener memory (`ctx.last_openers`) + `avoid_opening_like`.

- **`templates.py` / `textstyle.py`**
  - Short, label-free seeds and helpers (`weave_report` etc.).

---

## Anti-Repetition Summary

- **Memory**: last opener per role stored and passed to NLG as `avoid_opening_like`.
- **Prompt rules**: “Do not start with: ‘<last opener>’.”
- **Post-processing**: strips labels and role echoes, fixes punctuation, dedupes lines.
- **Variation pools**: multiple interchangeable phrasings per event type.

---

## Troubleshooting

- **Ollama connection errors**  
  Ensure the service is running and the host/port in `NLGConfig` match your setup.

- **Missing weekly reports**  
  Verify your scheduler (in `run.py`) calls `engine.weekly_report` once per week and that `--weeks` > 0.

- **Duplicate or label-y lines**  
  Use the modified `templates.py`, `nlg.py`, and `generator.py`. Keep `nlg_mode` as `full` or `paraphrase` so sanitization runs.

- **Windows timestamp formatting**  
  Already handled in `Message.as_whatsapp()`.

---

## Extending

- **New events**: add a seed in `templates.py`, a builder in `generator.py`, and wire facts → NLG.
- **New roles**: add a voice in `voices.py`, tone in `nlg.py`’s `ROLE_TONES`, and a builder in `generator.py`.
- **More variance**: extend variation pools; keep seeds brief and label-free.

---

## License

See `LICENSE` in your repository. Add one if missing.

---

## TL;DR

- Run:
  ```bash
  python -m src.run --weeks 8 --nlg_provider ollama --nlg_mode full --llm_model llama3.1:8b
  ```
- Orchestrator builds events + facts → seeds (label-free) → local NLG → cleaned WhatsApp-style lines.  
- Repetition minimized via opener memory, prompt rules, variation pools, and post-processing.
