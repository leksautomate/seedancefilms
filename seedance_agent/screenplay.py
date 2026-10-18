"""Screenplay layout to the one-line layout the segmenter reads.

Scripts are often pasted in the standard screenplay layout:

    RICHARD
    (laughing, loud, glass raised)
    Look at her! A primary school teacher ...

The segmenter reads `NAME: (delivery) line`. Without this step the delivery note is taken for the spoken line and the real line for
action, and the dialogue check would then compare the prompt against the wrong words. A script already in `NAME: line` form is
returned unchanged.
"""
from __future__ import annotations

import re

CUE = re.compile(r"^[A-Z][A-Z0-9 .'\-]{0,38}?(?:\s*\((?:CONT'?D\.?|CONTINUED|V\.?O\.?|O\.?S\.?|O\.?C\.?|OFF|ON PHONE)\))*\s*$")
NOT_A_CUE = re.compile(r"^(?:INT|EXT|I/E|SCENE|CUT|FADE|SMASH|DISSOLVE|MATCH|BACK|END|TITLE|TEXT|SUPER|CLIP|HOOK|FLASHBACK|MONTAGE|THE END|CONTINUED)\b", re.IGNORECASE)
PAREN = re.compile(r"^\(([^()]*)\)$")
TAIL = re.compile(r"\s*\((?:CONT'?D\.?|CONTINUED|V\.?O\.?|O\.?S\.?|O\.?C\.?|OFF|ON PHONE)\)")


def _is_cue(line: str) -> bool:
    s = line.strip()
    if not s or s.endswith((".", ":", "!", "?")) or NOT_A_CUE.match(s):
        return False
    return bool(CUE.match(s)) and any(c.isalpha() for c in s)


def normalize(text: str) -> str:
    lines = [re.sub(r"\*\*|__", "", l).rstrip() for l in text.replace("\r\n", "\n").split("\n")]
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        prev_blank = not out or not out[-1].strip()
        if prev_blank and _is_cue(line) and nxt and not _is_cue(nxt):
            name = TAIL.sub("", line.strip()).strip()
            j, note = i + 1, ""
            m = PAREN.match(lines[j].strip())
            if m:
                note = "(%s) " % m.group(1).strip()
                j += 1
                while j < len(lines) and not lines[j].strip():   # pasted scripts often leave blank lines after the note
                    j += 1
            body = []
            while j < len(lines) and lines[j].strip():
                body.append(lines[j].strip())
                j += 1
            if body:
                out.append("%s: %s%s" % (name, note, " ".join(body)))
                i = j
                continue
        out.append(line)
        i += 1
    return "\n".join(out)
