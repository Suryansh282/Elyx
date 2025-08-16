import os
from typing import List, Dict
from .schemas import ChatMessage

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

def _format_evidence(chats: List[ChatMessage], ids: List[int]) -> str:
    indexed = {c.id: c for c in chats}
    bits = []
    for cid in ids:
        c = indexed.get(cid)
        if c:
            bits.append(f"[{c.id}] {c.date} {c.sender}: {c.text}")
    return "\n".join(bits)

def offline_why_answer(decision: Dict, chats: List[ChatMessage]) -> str:
    """Deterministic fallback: stitch reasons + evidence into an explanation."""
    lines = [f"Decision: {decision['title']} on {decision['date']}.", decision["description"]]
    if decision.get("reasons"):
        lines.append("Reasons & evidence:")
        for r in decision["reasons"]:
            evidence_str = ", ".join(f"[{i}]" for i in r.get("evidence_ids", []))
            lines.append(f"- {r['text']} (evidence: {evidence_str})")
    return "\n".join(lines)

def offline_persona_summary(before: str, after: str) -> str:
    return f"Before: {before}\nAfter: {after}\nΔ: Transition captured based on referenced chat IDs."

# (Optional) You can add an OpenAI-powered function here if you want:
# def openai_answer(prompt: str) -> str: ...
# In this MVP, we keep everything offline-safe.
