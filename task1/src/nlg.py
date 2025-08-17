"""Local NLG via Ollama (with cache off, jitter, few-shot, and post-cleanup).

Two modes:
  * paraphrase: rewrite base bodies in a WhatsApp tone (safer)
  * full      : compose BODY only from facts (best for non-templated feel)

Natural chat features:
  * Few-shot style examples (style-only) to steer tone.
  * Role-specific tones; optional greetings only for team roles.
  * Post-cleanup that removes duplicate lines, polishes punctuation, and varies repeated openers.
  * Random jitter in temperature/top_p/num_predict for variability.
  * Cache disabled by default so each run differs.

This file is where we call the local LLM. The generator passes (role, event,
header, base_body, facts); in FULL mode we only use facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, List
import json
import urllib.request
import urllib.error
import socket
import hashlib
import re
import random


# -----------------------------
# Config
# -----------------------------

@dataclass
class NLGConfig:
    provider: str = "none"          # "none" | "ollama"
    mode: str = "paraphrase"        # "off" | "paraphrase" | "full"
    model: str = "llama3.1:8b"      # change via CLI if needed
    host: str = "http://localhost:11434"
    timeout_sec: int = 6
    temperature: float = 0.7
    top_p: float = 0.95
    num_predict: int = 160
    enable_cache: bool = False      # OFF: allow variation on each run


# ---- Role tones & helpers ----

ROLE_TONES = {
    "Ruby": (
        "empathetic, proactive, logistics, confirmations; keeps friction low; "
        "hand-offs to specialists"
    ),
    "Dr. Warren": "authoritative, precise, plain-English clinical; short risks/benefits",
    "Advik": "analytical, data trends, short hypothesis + next action",
    "Carla": "practical nutrition, behavior change, short why",
    "Rachel": "direct coaching, form-first cues, regress/progress options",
    "Neel": "strategic, big-picture, ROI and milestones",
}

STYLE_HINTS = [
    "warm & brief",
    "to-the-point",
    "casual but clear",
    "executive and concise",
    "friendly and practical",
    "matter-of-fact",
]


def _is_member_role(role: str) -> bool:
    r = (role or "").strip().lower()
    return r in {"rohan", "member", "client", "user"}


def _few_shot_examples(role: str) -> str:
    """Tiny style-only examples (NOT content)."""
    ex = [
        "- Morning HRV dipped a bit. Let’s keep dinner earlier and cut caffeine after lunch. I’ll check back Thursday.",
        "- I held your 7–7:30 gym slots and sent hotel swaps. Want me to lock those?",
        "- Numbers are moving the right way, not at target yet. If you’re okay, we stay the course two more weeks.",
        "- Travel week ahead—pushed heavier sessions to non-flight days and left mobility on travel days.",
        "- Appreciate the update. I’ll loop Carla in for the menu and confirm with Sarah on timing.",
    ]
    picked = random.sample(ex, k=3)
    return "\n".join(picked)


# -----------------------------
# Post-processing helpers
# -----------------------------

_DUP_END_PUNC = re.compile(r"[.?!…]+$")
_SPACE_BEFORE_PUNC = re.compile(r"\s+([,.;!?])")
_MERGE_PUNC = re.compile(r"([,;])([^\s])")
_MULTI_DOTS = re.compile(r"\.{2,}")
_TRAIL_COLON_SEMI = re.compile(r"(?m)[:;]\s*$")
_MULTI_SPACES = re.compile(r"\s{2,}")
_END_BANG_Q_DOT = re.compile(r"([?!])\s*\.")  # e.g., "?.", "!."

def _normalize_for_dupe(line: str) -> str:
    s = line.strip().lower()
    s = _DUP_END_PUNC.sub("", s)
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

def _cap_first_alpha(line: str) -> str:
    m = re.match(r"^(\s*)([a-z])", line)
    if m:
        pre, ch = m.group(1), m.group(2)
        return f"{pre}{ch.upper()}{line[m.end():]}"
    return line

def _ensure_end_punct(line: str) -> str:
    if not line:
        return line
    if line[-1] not in ".?!":
        return line + "."
    return line

def _tidy_text_block(text: str) -> str:
    """Grammar/punctuation cleanup for the whole block."""
    if not text:
        return text
    t = text.strip()
    # Normalize punctuation combos and spaces
    t = t.replace("?.", "?").replace("!.", "!")
    t = _END_BANG_Q_DOT.sub(r"\1", t)
    t = _MULTI_DOTS.sub(".", t)
    t = _MULTI_SPACES.sub(" ", t)
    t = _SPACE_BEFORE_PUNC.sub(r"\1", t)       # remove spaces before punctuation
    t = _MERGE_PUNC.sub(r"\1 \2", t)           # ensure space after comma/semicolon
    t = _TRAIL_COLON_SEMI.sub(".", t)          # convert trailing : or ; to .
    # Split lines, trim, capitalize first alpha, ensure end punctuation
    lines = [_ensure_end_punct(_cap_first_alpha(L.strip())) for L in t.splitlines() if L.strip()]
    return "\n".join(lines).strip()

def _vary_common_openers(lines: List[str]) -> List[str]:
    """Swap repeated openers with synonyms to reduce monotony (facts preserved)."""
    out = []
    for ln in lines:
        s = ln.strip()

        # Likely / Probably / Hunch
        if re.match(r"(?i)likely\s", s) and random.random() < 0.6:
            s = re.sub(r"(?i)^likely\s", random.choice(["Probably ", "My hunch is ", "Signals point to "]), s, count=1)

        # Let's do / Let's try / Let's go with
        if re.match(r"(?i)let['’]s do\s", s) and random.random() < 0.6:
            s = re.sub(r"(?i)^let['’]s do\s", random.choice(["Let’s try ", "Let’s go with "]), s, count=1)

        # Current numbers are / Latest numbers / Right now
        if re.match(r"(?i)current numbers are\s", s) and random.random() < 0.6:
            s = re.sub(r"(?i)^current numbers are\s", random.choice(["Latest numbers: ", "Right now: "]), s, count=1)

        # Results are in —
        if re.match(r"(?i)results are in\s?[—\-:]\s*", s) and random.random() < 0.6:
            s = re.sub(r"(?i)^results are in\s?[—\-:]\s*", random.choice(["Got the results — ", "Panel summary — "]), s, count=1)

        # I’m noting / Noted / From your update,
        if re.match(r"(?i)i['’]m noting\s", s) and random.random() < 0.5:
            s = re.sub(r"(?i)^i['’]m noting\s", random.choice(["Noted ", "From your update, "]), s, count=1)

        out.append(s)
    return out

def _finalize_message(text: str) -> str:
    """Full cleanup pipeline: split → dedupe → vary → tidy → grammar fixes."""
    # Split on lines the model emitted (we encourage 2–4 lines)
    lines = [L.strip() for L in text.splitlines() if L.strip()]
    if not lines:
        return text.strip()

    # Remove exact/near duplicates
    lines = _dedupe_lines(lines)

    # Vary common repeated openers
    lines = _vary_common_openers(lines)

    # Re-apply dedupe in case variation created collisions
    lines = _dedupe_lines(lines)

    out = _tidy_text_block("\n".join(lines))

    # Fix common fused-phrase glitches and awkward constructions
    out = re.sub(r"(?i)let[’']s stick with (?:continue|stay the course)\b", "Let’s stay the course", out)
    out = re.sub(r"(?i)let[’']s go with keep\b", "Let’s keep", out)
    out = re.sub(r"(?i)let[’']s go with ask\b", "Ask", out)
    out = re.sub(r"(?i)put attention on\b", "focus on", out)

    # Final punctuation pass
    out = out.replace("?.", "?").replace("!.", "!")
    out = _END_BANG_Q_DOT.sub(r"\1", out)

    return out


class NLGEngine:
    def __init__(self, cfg: NLGConfig):
        self.cfg = cfg
        self._cache: Dict[str, str] = {}

    @classmethod
    def from_args(cls, provider: str, mode: str, model: str) -> Optional["NLGEngine"]:
        if provider == "none" or mode == "off":
            return None
        return cls(NLGConfig(provider=provider, mode=mode, model=model))

    def warmup(self) -> None:
        if self.cfg.provider != "ollama":
            return
        try:
            _ = self._ollama_generate("Reply with OK.")
        except Exception:
            pass

    def enhance(
        self,
        role: str,
        event: str,
        header: str,
        base_body: str,
        facts: Optional[Dict[str, str]] = None,
    ) -> str:
        if self.cfg.provider == "none" or self.cfg.mode == "off":
            return base_body

        facts = facts or {}
        key = self._key(role, event, header, base_body, facts, self.cfg.mode, self.cfg.model)
        if self.cfg.enable_cache and key in self._cache:
            return self._cache[key]

        try:
            if self.cfg.mode == "paraphrase":
                prompt = self._prompt_paraphrase(role, event, header, base_body, facts)
            elif self.cfg.mode == "full":
                prompt = self._prompt_full(role, event, header, facts)
            else:
                return base_body

            text = self._ollama_generate(prompt).strip()
            if not text:
                return base_body

            # Safety strip + normalization
            text = self._sanitize(text, role=role, header=header)

            # Final polish to remove repetition/rough edges
            text = _finalize_message(text)

            if self.cfg.enable_cache:
                self._cache[key] = text
            return text
        except Exception:
            return base_body

    # -------------------------
    # Prompts
    # -------------------------

    def _prompt_paraphrase(
        self, role: str, event: str, header: str, base_body: str, facts: Dict[str, str]
    ) -> str:
        tone = ROLE_TONES.get(role, "concise and helpful")
        sender_rule = (
            "- Sender is the MEMBER. Do NOT greet or address yourself by name. "
            "Write 1–2 short sentences max. Keep it direct.\n"
            if _is_member_role(role)
            else
            "- Sender is an ELYX TEAM MEMBER. You may greet with the member’s name ONLY if it feels "
            "natural; don’t greet every time. Prefer 0–1 sentence greeting, then content.\n"
        )
        style_hint = facts.get("style_hint", random.choice(STYLE_HINTS))
        avoid = facts.get("avoid_opening_like", "")
        avoid_line = f"- Do not start with: “{avoid}”. Use a different opening.\n" if avoid else ""
        facts_lines = "\n".join(f"- {k}: {v}" for k, v in facts.items()) if facts else "-"

        return (
            f"You are '{role}' writing a short WhatsApp-style message for event '{event}'.\n"
            f"Style: {tone}. Adopt this nuance: {style_hint}.\n"
            f"{sender_rule}"
            f"{avoid_line}"
            "- Keep it human and brief (2–4 short sentences). Avoid bullet points and labels.\n"
            "- Avoid colon-led or dash-led fragments (e.g., 'Watch-outs:', 'Focus:', 'Panel summary —'). Use plain sentences.\n"
            "- Include hand-offs or confirmations only if natural.\n"
            "- Preserve ALL concrete facts and numbers; do not invent anything.\n"
            f"- DO NOT include the header line '{header}'. Output BODY ONLY.\n"
            "- Vary openings; don’t always greet. If you greet, put it on its own line.\n"
            "- Do not repeat the same opening across lines; avoid starting two lines with the same 1–2 words.\n"
            "- If you find yourself repeating a point, drop the repeat.\n\n"
            "Examples (style only, do not copy facts or exact wording):\n"
            f"{_few_shot_examples(role)}\n\n"
            "Facts (source of truth):\n"
            f"{facts_lines}\n\n"
            "Original body to paraphrase:\n"
            f"{base_body}\n\n"
            "Rewrite naturally now (BODY ONLY):"
        )

    def _prompt_full(self, role: str, event: str, header: str, facts: Dict[str, str]) -> str:
        tone = ROLE_TONES.get(role, "concise and helpful")
        sender_rule = (
            "- Sender is the MEMBER. Do NOT greet or use the member’s name. "
            "Write 1–2 short sentences max; keep it direct.\n"
            if _is_member_role(role)
            else
            "- Sender is an ELYX TEAM MEMBER. You may greet with the member’s name ONLY if it feels "
            "natural; avoid greeting in every message. If you greet, put the greeting on its own line.\n"
        )
        style_hint = facts.get("style_hint", random.choice(STYLE_HINTS))
        avoid = facts.get("avoid_opening_like", "")
        avoid_line = f"- Do not start with: “{avoid}”. Use a different opening.\n" if avoid else ""
        facts_lines = "\n".join(f"- {k}: {v}" for k, v in (facts or {}).items()) or "-"

        return (
            f"You are '{role}' writing a WhatsApp-style message for '{event}'.\n"
            f"Tone: {tone}. Adopt this nuance: {style_hint}.\n"
            f"{sender_rule}"
            f"{avoid_line}"
            "- Output 2–4 short sentences. Use plain language; no bullet points, no labels.\n"
            "- Mention logistics/confirmations briefly if implied by facts.\n"
            "- Base the message ONLY on these facts. Do NOT invent or speculate.\n"
            f"- DO NOT include the header '{header}'. Output BODY ONLY.\n"
            "- Do NOT repeat the same opening across lines; vary transitions.\n"
            "- If a thought would repeat, omit the repeat.\n\n"
            "Examples (style only, do not copy facts or exact wording):\n"
            f"{_few_shot_examples(role)}\n\n"
            "Facts (strict source of truth):\n"
            f"{facts_lines}\n\n"
            "Compose the BODY ONLY now:"
        )

    # -------------------------
    # Sanitizers
    # -------------------------

    def _sanitize(self, text: str, role: str, header: str) -> str:
        s = text.strip()

        # 1) strip accidental header echoes
        header_patterns = [
            r"^\s*weekly report\s*:?\s*",
            r"^\s*medical check-?in\s*:?\s*",
            r"^\s*nutrition update\s*:?\s*",
            r"^\s*exercise update\s*:?\s*",
            r"^\s*travel adaptation.*?:\s*",
            r"^\s*diagnostics results\s*:?\s*",
            r"^\s*ordering your diagnostic panel\s*:?\s*",
            r"^\s*wearable note\s*:?\s*",
        ]
        for pat in header_patterns:
            s = re.sub(pat, "", s, flags=re.IGNORECASE)

        # 2) remove role prefixes
        s = re.sub(r"^(ruby|dr\.?\s*warren|advik|carla|rachel|neel)\s*[:\-–]\s*", "", s, flags=re.IGNORECASE)

        # 3) remove leading bullets
        s = re.sub(r"(?m)^\s*-\s*", "", s)

        # 4) remove common labels (keep content) — accept colon or dash after label
        label_heads = [
            r"watch[-\s]?outs", r"flags", r"risks?",
            r"focus for next week", r"what we[’']ll prioritize", r"next[-\s]?week focus",
            r"actions?", r"observation", r"recommendation",
            r"symptoms?", r"review", r"plan(?: for (?:next|this) week)?", r"form cues?",
            r"hypothesis", r"next", r"summary", r"interpretation", r"options?",
            r"from your log", r"training update", r"my read", r"panel summary",
            r"on labs/vitals", r"on symptoms",
            r"on the plus side", r"i[’']m keeping an eye on", r"one thing to watch", r"worth flagging",
            r"latest numbers",
        ]
        for lh in label_heads:
            # Strip label + colon OR em/en dash
            s = re.sub(rf"(?mi)^\s*{lh}\s*[:—\-]\s*", "", s)

        # Also strip "On labs/vitals," or "On symptoms," forms
        s = re.sub(r"(?mi)^\s*on\s+(labs/vitals|symptoms)\s*[:,]\s*", "", s)

        # 5) member never greets self
        if _is_member_role(role):
            s = re.sub(r"^\s*(hi|hello|hey)\s+rohan\s*[,–-]*\s*", "", s, flags=re.IGNORECASE)

        # 6) punctuation cleanup
        s = s.replace("?.", "?").replace("!.", "!")
        s = _END_BANG_Q_DOT.sub(r"\1", s)
        s = re.sub(r"\.\.+", ".", s)
        s = re.sub(r"\s{2,}", " ", s)
        s = re.sub(r"(?m)[:;]\s*$", ".", s)
        s = re.sub(r"\n{3,}", "\n\n", s)

        return s.strip()

    # -------------------------
    # HTTP call
    # -------------------------

    def _ollama_generate(self, prompt: str) -> str:
        url = f"{self.cfg.host}/api/generate"

        # add small jitter for variety
        t = max(0.2, min(1.2, self.cfg.temperature + random.uniform(-0.15, 0.15)))
        top_p = max(0.5, min(0.99, self.cfg.top_p + random.uniform(-0.03, 0.03)))
        num_predict = int(max(96, min(240, self.cfg.num_predict + random.randint(-16, 24))))

        payload = {
            "model": self.cfg.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": t,
                "top_p": top_p,
                "num_predict": num_predict,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout_sec) as resp:
                body = resp.read().decode("utf-8")
                obj = json.loads(body)
                return obj.get("response", "")
        except (urllib.error.URLError, socket.timeout, TimeoutError):
            return ""  # quick fallback

    # -------------------------
    # Cache key
    # -------------------------

    @staticmethod
    def _key(role, event, header, base_body, facts, mode, model) -> str:
        h = hashlib.sha256()
        h.update(mode.encode()); h.update(model.encode())
        h.update((role or "").encode()); h.update((event or "").encode()); h.update((header or "").encode())
        h.update((base_body or "").encode())
        try:
            facts_json = json.dumps(facts or {}, sort_keys=True).encode()
        except Exception:
            facts_json = str(facts).encode()
        h.update(facts_json)
        return h.hexdigest()
