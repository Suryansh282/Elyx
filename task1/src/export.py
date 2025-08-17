"""Export utilities for JSONL and WhatsApp-like text."""
from __future__ import annotations

from pathlib import Path
from typing import List
import json

from .content.generator import Message


def export_jsonl(messages: List[Message], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for m in messages:
            f.write(json.dumps(m.as_json(), ensure_ascii=False) + "\n")


def export_txt(messages: List[Message], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for m in messages:
            f.write(m.as_whatsapp() + "\n")
    # Summary footer
    footer = "\n--- End of conversation ---\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(footer)
