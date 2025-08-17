# Prompts / LLM Guidance

This project keeps **logic & validators** in code (events, metrics, schedules) and uses a **local LLM** (Ollama) only to shape the **BODY** of each message into WhatsApp-like language. The **header** (e.g., `Weekly report:`) is always added by the generator so validators can count events.

## Modes

- **paraphrase** (recommended): rewrite our safe, factual body into a natural tone.
- **full**: compose a fresh body from facts (headers still added by code). Slightly freer, still fact-anchored.

## Role tones

- **Ruby**: empathetic, proactive, logistics + confirmations; hand-offs.
- **Dr. Warren**: authoritative, precise, plain-English clinical; risk/benefit.
- **Advik**: analytical, data trends, hypothesis + next-step experiments.
- **Carla**: practical nutrition, behavior change, explain “why” briefly.
- **Rachel**: direct coaching, form-first, regress/progress cues.
- **Neel**: strategic, big-picture, milestones and ROI.

## Paraphrase prompt (BODY only)

- Keep it human and brief (2–5 short lines; 3–6 bullets max).
- Preserve all facts and numbers; **no invention**.
- Do **not** include the header.
- For team roles: greeting is optional; if used, put it on its own line; add logistics/confirmation when natural.
- For member: **no greeting**; 1–2 direct sentences.

## Full prompt (BODY only)

- 2–5 short lines, plain language.
- Draw only from provided **facts**; no speculation.
- Do **not** include the header.
- Same role rules re: greeting and tone.

## Safety rails

- Code **prepends headers** for validator stability.
- Sanitizers strip accidental headers, role prefixes, and “Hi Rohan” when the sender is the member.
- Low `num_predict` and small local models → fast, deterministic-enough runs.

## Suggested CLI

Paraphrase (best balance):
```bash
python -m src.run --seed 42 --weeks 34 --tz Asia/Singapore --output_dir ./demo \
  --nlg_provider ollama --nlg_mode paraphrase --llm_model phi3:mini
