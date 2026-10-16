"""Loads the agent's instructions and fills in the movie-specific parts."""
from __future__ import annotations

import json
from pathlib import Path

from .skills_bridge import SKILLS

DIR = Path(__file__).resolve().parent / "prompts"
EXAMPLES = SKILLS / "seedance-scene-prompter" / "examples"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load(name: str) -> str:
    return _read(DIR / name)


def examples_block() -> str:
    """The user's own prompts, shown to the writer as the house style."""
    parts = []
    for fname, label in (("01-kitchen-jeans-15s.txt", "EXAMPLE 1: a full-style prompt for a new 15 second clip"),
                         ("02-kitchen-jeans-extend.txt", "EXAMPLE 2: the extension prompt that continues Example 1")):
        p = EXAMPLES / fname
        if p.exists():
            parts.append("### %s\n\n%s" % (label, _read(p).strip()))
    return "\n\n".join(parts)


def writer_system(movie: dict) -> str:
    s = movie.get("settings", {})
    text = load("writer.md")
    text = text.replace("{examples}", examples_block())
    text = text.replace("{format_line}", s.get("format_line") or "fast-paced cinematic adult animated scene")
    text = text.replace("{request_s}", "15")
    context = {
        "movie": movie.get("name"),
        "settings": {k: v for k, v in s.items() if v},
        "bible": movie.get("bible", {}),
    }
    return text + "\n\n# This movie\n\n```json\n%s\n```\n" % json.dumps(context, indent=2, ensure_ascii=False)


def analyst_system() -> str:
    return load("analyst.md")


def revise_note() -> str:
    return load("revise.md")
