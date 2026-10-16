"""Loads the segmenter and the dialogue-timing script from the skills folder.

The two scripts in .claude/skills are the single source of truth for the numbers. The agent imports them
instead of keeping a second copy, so a calibration change there shows up here.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
_cache: dict = {}


def _load(name: str, relpath: str):
    if name in _cache:
        return _cache[name]
    path = SKILLS / relpath
    if not path.exists():
        raise FileNotFoundError("Cannot find %s. The agent expects the skills folder at %s." % (path, SKILLS))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _cache[name] = mod
    return mod


def _seg():
    return _load("segment_episode", "episode-segmenter/scripts/segment_episode.py")


def _tim():
    return _load("dialogue_timing", "seedance-scene-prompter/scripts/dialogue_timing.py")


def segment(text: str, **overrides) -> list[dict]:
    """Split an episode script into clip-sized segments (see episode-segmenter)."""
    mod = _seg()
    args = mod.build_parser().parse_args(["-"])
    for k, v in overrides.items():
        if v is not None and hasattr(args, k):
            setattr(args, k, v)
    return mod.build(text, args)


def timing(prompt: str, limit: float, wps: float | None = None) -> dict:
    """Count spoken words per shot in a finished prompt and estimate its running time."""
    mod = _tim()
    a = mod.build_parser().parse_args(["-"])
    wps = wps or a.wps
    rows = mod.analyse(prompt, wps, a.line_gap, a.pause, a.pad, a.min_shot)
    total = round(sum(r["shot_s"] for r in rows), 1)
    return {
        "shots": len(rows),
        "dialogue_lines": sum(r["lines"] for r in rows),
        "dialogue_words": sum(r["words"] for r in rows),
        "speaking_s": round(sum(r["speaking_s"] for r in rows), 1),
        "estimated_s": total,
        "limit_s": limit,
        "verdict": mod.verdict(total, limit),
        "rows": rows,
    }


def shot_blocks(prompt: str) -> list[tuple[str, str, str]]:
    """(number, heading, body) for every SHOT block in a prompt."""
    return _tim().split_shots(prompt)


def dialogue_in(block: str) -> list[str]:
    return _tim().dialogue_lines(block)
