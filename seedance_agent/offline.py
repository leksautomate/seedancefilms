"""Offline drafter: builds a valid prompt straight from the script's events, with no model.

This is a template, not a creative writer. It exists so the pipeline (segmenting, filing, linting, plan page)
can be run and tested without an API key, and so a person still gets usable drafts when no model is available.
The live agent writes the real prompts. Everything this module writes is marked as an offline draft.
"""
from __future__ import annotations

import re

from .util import norm_key, title_case

DEFAULT_FORMAT_LINE = "fast-paced cinematic adult animated scene"


def tag_for(name: str, bible: dict, kind: str = "characters") -> str:
    entry = (bible.get(kind) or {}).get(name) or {}
    return entry.get("tag") or "@ TAG %s" % name.upper()


def location_tag(segment: dict, bible: dict) -> tuple[str, str]:
    loc = segment.get("location") or ""
    for name, entry in (bible.get("locations") or {}).items():
        if norm_key(name) == norm_key(loc):
            return title_case(name), entry.get("tag") or "@ TAG %s" % name.upper()
    nice = title_case(loc) if loc else "the location"
    return nice, "@ TAG %s" % (loc.upper() if loc else "LOCATION")


def _voice_block(name: str, bible: dict) -> tuple[str, bool]:
    voice = ((bible.get("characters") or {}).get(name) or {}).get("voice")
    if voice:
        return "%s'S VOICE:\n\n%s" % (name.upper(), voice.strip()), False
    return ("%s'S VOICE:\n\nA natural voice that suits %s. Keep exactly the same voice, pitch and delivery in every shot." % (
        name.upper(), title_case(name)), True)


def _delivery(text: str) -> str:
    t = text.strip()
    if t.endswith("?"):
        return "asking"
    if t.endswith("!") or (t.isupper() and len(t) > 3):
        return "loudly"
    if t.endswith(("...", "\u2026")):
        return "trailing off"
    return "clearly"


def draft(segment: dict, bible: dict, settings: dict, prev: dict | None = None) -> dict:
    """Return {'prompt', 'shots', 'brief', 'carry_over', 'assumptions'} for one segment."""
    events = [e for e in segment.get("events", []) if e.get("kind") != "transition"]
    chars = segment.get("characters", [])
    speakers: list[str] = []
    for e in events:
        if e["kind"] == "dialogue" and e["speaker"] and e["speaker"] not in speakers:
            speakers.append(e["speaker"])
    loc_name, loc_tag = location_tag(segment, bible)
    fmt = settings.get("format_line") or DEFAULT_FORMAT_LINE
    request = int(segment.get("request_s") or settings.get("clip_seconds", 30))
    assumptions = ["Drafted offline from a template (no model was used). Treat it as a starting point."]

    mode = segment.get("mode", "single")
    lines: list[str] = []
    if mode == "extend":
        last_line = (prev or {}).get("last_line")
        if last_line:
            lines.append("Extend the @ TAG VIDEO from the exact final frame after %s says:\n\n\u201c%s\u201d" % (
                (prev or {}).get("last_speaker") or "the last speaker", last_line))
        else:
            lines.append("Extend the @ TAG VIDEO from the exact final frame of the previous clip.")
        lines.append("Continue the same scene in %s with the exact same character designs, clothing, lighting, atmosphere, "
                     "framing style, and emotional continuity." % loc_name)
    else:
        first = "Create a %ds %s." % (request, fmt)
        if mode == "new-chain":
            first = ("Create a %ds %s that starts exactly from the last frame of the previous clip "
                     "(use it as the first-frame reference @Image 1)." % (request, fmt))
        lines.append(first)
        who = " and ".join("%s %s" % (n, tag_for(n, bible)) for n in chars) or "the characters"
        lines.append("%s %s in the %s %s." % (who, "are" if len(chars) > 1 else "is", loc_name, loc_tag))
        if chars:
            lines.append("Preserve the exact established designs, proportions, clothing, %s %s, lighting, colors, and visual style for %s." % (
                loc_name, loc_tag, " and ".join("%s %s" % (n, tag_for(n, bible)) for n in chars)))
    lines.append("IMPORTANT:\n\nUse ONLY hard cuts between shots.\nNO tracking shots, camera slides, whip pans, or continuous camera transitions.")
    tone = (settings.get("tone") or "").strip()
    lines.append("Keep the pacing fast, sharp, and cinematic%s." % ((", and " + tone) if tone and tone.lower() not in ("sharp", "cinematic", "fast") else ""))
    lines.append("NO music. Only natural ambience, subtle object sounds, and dialogue.")
    if mode in ("single", "generate", "new-chain"):
        for sp in speakers:
            block, assumed = _voice_block(sp, bible)
            lines.append(block)
            if assumed:
                assumptions.append("No voice was given for %s. A neutral placeholder voice was used; set one in movie.json." % sp)

    # ---- shots ---------------------------------------------------------
    shots: list[dict] = []
    body: list[str] = []
    n = 0
    scale_cycle = ["MEDIUM CLOSE-UP", "CLOSE-UP", "MEDIUM SHOT"]
    i = 0
    dlg_index = 0
    pending_action: list[str] = []

    def push(heading: str, desc: list[str], dialogue: tuple | None, seconds: float, scale: str, func: str) -> None:
        nonlocal n
        n += 1
        block = ["SHOT %d \u2014 %s" % (n, heading)]
        block.extend(desc)
        if dialogue:
            sp, text = dialogue
            voice_ref = "In the SAME established voice,"
            block.append("%s %s says, %s:\n\n\u201c%s\u201d" % (voice_ref, sp, _delivery(text), text))
        block.append("HARD CUT.")
        body.append("\n\n".join(block))
        shots.append({"n": n, "scale": scale, "angle": "eye level", "camera": "locked-off", "seconds": round(seconds, 1),
                      "function": func, "dialogue": dialogue[1] if dialogue else None})

    while i < len(events):
        e = events[i]
        if e["kind"] == "establish":
            push("ESTABLISHING WIDE SHOT \u2014 EYE LEVEL", ["Wide locked-off shot of %s %s, showing the whole space and where everyone is." % (loc_name, loc_tag)],
                 None, e["seconds"], "wide", "establish the place")
            i += 1
            continue
        if e["kind"] in ("action", "sfx"):
            group = [e["text"]]
            secs = e["seconds"]
            j = i + 1
            while j < len(events) and events[j]["kind"] == e["kind"] and events[j].get("seconds", 9) <= 0.6:
                group.append(events[j]["text"])
                secs += events[j]["seconds"]
                j += 1
            nxt = events[j] if j < len(events) else None
            if nxt is not None and nxt["kind"] == "dialogue" and e["kind"] == "action":
                pending_action = group
                i = j
                continue
            push("%s \u2014 EYE LEVEL" % ("INSERT SHOT" if e["kind"] == "sfx" else "MEDIUM SHOT"), [" ".join(group)], None, secs,
                 "insert" if e["kind"] == "sfx" else "medium", "show the action")
            i = j
            continue
        if e["kind"] == "dialogue":
            scale = scale_cycle[dlg_index % len(scale_cycle)]
            desc = list(pending_action)
            pending_action = []
            subject = re.match(r"\s*([A-Z][A-Z0-9'\-]{2,})\b", desc[0]) if desc else None
            other = bool(subject and subject.group(1) != e["speaker"] and subject.group(1) in chars)
            if other:  # the action is about someone else, so do not head the shot with the speaker
                heading = "MEDIUM SHOT \u2014 EYE LEVEL"
            else:
                heading = "%s ON %s \u2014 EYE LEVEL" % (scale, e["speaker"])
            if not desc:
                desc = ["%s is the focus of the frame." % title_case(e["speaker"])]
            push(heading, desc, (e["speaker"], e["text"]), e["seconds"], scale.lower(), "deliver the line")
            dlg_index += 1
            i += 1
            continue
        i += 1
    if pending_action:
        push("MEDIUM SHOT \u2014 EYE LEVEL", [" ".join(pending_action)], None, 1.5, "medium", "show the action")

    ending = "CUT TO BLACK." if segment.get("part") == segment.get("parts") else "END HERE."
    prompt = "\n\n".join(lines + body + [ending]) + "\n"

    last_dlg = next((e for e in reversed(events) if e["kind"] == "dialogue"), None)
    carry = {"last_frame": (events[-1]["text"] if events else ""), "positions": "as in the script", "props": "", "costume": "", "lighting": ""}
    brief = {
        "purpose": "Deliver this beat of the scene.",
        "subject": ", ".join(chars) or "see prompt",
        "subject_action": "see shot list",
        "camera": "locked-off framing with hard cuts",
        "environment": "%s %s" % (loc_name, loc_tag),
        "lighting": "as established in the scene",
        "visual_direction": settings.get("style_lock") or "match the established look",
        "stability": ["Keep each character's design, clothing and voice identical in every shot."],
        "must_get": [s["dialogue"] for s in shots if s.get("dialogue")][:3],
        "cut_first": [],
    }
    return {"prompt": prompt, "shots": shots, "brief": brief, "carry_over": carry, "assumptions": assumptions,
            "last_line": last_dlg["text"] if last_dlg else None, "last_speaker": last_dlg["speaker"] if last_dlg else None}
