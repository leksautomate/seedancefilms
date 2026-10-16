"""The gate every prompt passes before it is saved.

Errors block saving (the writer must fix them). Warnings are saved with the prompt and shown in the plan.
The most important check: the spoken lines in the prompt must be the script's lines, word for word.
The agent never rewrites, trims or invents dialogue.
"""
from __future__ import annotations

import re

from . import skills_bridge as sb
from .util import words

SHOT_HEAD = re.compile(r"^\s*(?:\*\*)?SHOT\s+(\d+)\b(.*)$", re.IGNORECASE | re.MULTILINE)
ENDING = re.compile(r"\b(END HERE|CUT TO BLACK)\b|^\s*END\.?\s*$", re.IGNORECASE)
PLACEHOLDER = re.compile(r"<[^>\n]{2,40}>|\{\{[^}]*\}\}|\[(?:TODO|INSERT|TBD|PLACEHOLDER)[^\]]*\]", re.IGNORECASE)
CAMERA_MOVES = re.compile(r"\b(tracking shot|dolly|whip pan|pan left|pan right|zoom|crane|orbit|handheld|steadicam|tilt up|tilt down)\b", re.IGNORECASE)


def _run_tokens(tokens: list[str], needle: list[str]) -> bool:
    n = len(needle)
    if not n:
        return True
    return any(tokens[i:i + n] == needle for i in range(0, len(tokens) - n + 1))


def spoken_in_prompt(prompt: str) -> list[str]:
    out = []
    for _n, _h, body in sb.shot_blocks(prompt):
        out.extend(sb.dialogue_in(body))
    return out


def lint(prompt: str, segment: dict, bible: dict, settings: dict, style: str = "full", prev: dict | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    text = prompt or ""
    if not text.strip():
        return {"errors": ["The prompt is empty."], "warnings": [], "timing": None}

    # 1. placeholders and size
    ph = PLACEHOLDER.search(text)
    if ph:
        errors.append("Placeholder left in the prompt: %r. Write the real text." % ph.group(0))
    if len(text) > 12000:
        errors.append("The prompt is %d characters. Keep it under 12000." % len(text))
    elif len(text) > 6500:
        warnings.append("The prompt is long (%d characters). Shorter prompts are followed more closely." % len(text))

    # 2. shot structure
    nums = [int(m.group(1)) for m in SHOT_HEAD.finditer(text)]
    if len(nums) < 2:
        errors.append("Use at least 2 shots, each starting with a line like 'SHOT 1 — MEDIUM SHOT — EYE LEVEL'.")
    elif nums != list(range(1, len(nums) + 1)):
        errors.append("Shot numbers must run 1, 2, 3 ... without gaps. Found: %s." % nums)
    if len(nums) > 14:
        errors.append("%d shots is too many for one clip. Merge shots." % len(nums))
    if style == "full":
        for m in SHOT_HEAD.finditer(text):
            rest = re.sub(r"[\s—–\-:]+", "", m.group(2))
            if not rest:
                warnings.append("SHOT %s has no shot type or angle in its heading." % m.group(1))
        if len(nums) >= 2 and not re.search(r"HARD CUT", text, re.IGNORECASE):
            warnings.append("No 'HARD CUT.' line between shots.")

    # 3. house-style header (full style)
    if style == "full":
        head = text.split("SHOT 1")[0] if "SHOT 1" in text else text
        if not (re.search(r"hard cuts?", head, re.IGNORECASE) and re.search(r"\bonly\b", head, re.IGNORECASE)):
            errors.append("The header must say 'Use ONLY hard cuts between shots.'")
        if not re.search(r"\bNO\s+MUSIC\b", text, re.IGNORECASE):
            errors.append("The header must say 'NO music' and list the allowed sounds.")
        if not re.search(r"(tracking|whip pan|camera slide)", head, re.IGNORECASE):
            warnings.append("The header does not forbid tracking shots, camera slides and whip pans.")
        if "IMPORTANT" not in text:
            warnings.append("No IMPORTANT block locking the details that must not drift.")

    # 4. camera moves outside the negating sentence
    if style == "full":
        for line in text.splitlines():
            if re.search(r"\b(NO|ONLY|never|not)\b", line, re.IGNORECASE):
                continue
            mv = CAMERA_MOVES.search(line)
            if mv:
                warnings.append("Camera move '%s' in a hard-cuts-only prompt: %s" % (mv.group(0), line.strip()[:70]))
                break

    # 5. ending
    tail = [l for l in text.strip().splitlines() if l.strip()][-3:]
    if not any(ENDING.search(l) for l in tail):
        errors.append("End the prompt explicitly: 'END HERE.' or 'CUT TO BLACK.'")

    # 6. dialogue: word for word, in order, nothing added
    expected = [e["text"] for e in segment.get("events", []) if e.get("kind") == "dialogue"]
    actual = spoken_in_prompt(text)
    exp_tokens = [t for line in expected for t in words(line)]
    act_tokens = [t for line in actual for t in words(line)]
    if exp_tokens != act_tokens:
        k = next((i for i, (a, b) in enumerate(zip(exp_tokens, act_tokens)) if a != b), min(len(exp_tokens), len(act_tokens)))
        want = " ".join(exp_tokens[max(0, k - 3):k + 4])
        have = " ".join(act_tokens[max(0, k - 3):k + 4])
        errors.append("Dialogue must match the script word for word and in order, and nothing may be added or dropped. "
                      "Around word %d the script has '%s' but the prompt has '%s'. Script lines: %s" % (
                          k + 1, want or "(end)", have or "(end)", " | ".join(expected) or "(none)"))

    # 7. timing
    limit = float(settings.get("clip_seconds", 15))
    timing = sb.timing(text, limit)
    if timing["verdict"] == "TOO LONG":
        errors.append("Estimated %.1fs against a %ds clip. Remove or merge non-dialogue shots or shorten action. "
                      "Do not cut dialogue." % (timing["estimated_s"], limit))
    elif timing["verdict"] == "TIGHT":
        warnings.append("Timing is tight: estimated %.1fs of %ds." % (timing["estimated_s"], limit))
    if timing["dialogue_words"] and timing["shots"] and timing["dialogue_lines"] > 2 * timing["shots"]:
        warnings.append("More than two spoken lines per shot on average.")

    # 8. tags and voices
    chars = bible.get("characters", {})
    speakers = []
    for e in segment.get("events", []):
        if e.get("kind") == "dialogue" and e.get("speaker") and e["speaker"] not in speakers:
            speakers.append(e["speaker"])
    if segment.get("mode") != "extend":  # an extension carries the designs in the source video
        for name in segment.get("characters", []):
            tag = (chars.get(name) or {}).get("tag")
            if tag and tag.lower() not in text.lower():
                (errors if name in speakers else warnings).append("Character %s is used but the tag '%s' is missing from the prompt." % (name, tag))
    if style == "full" and segment.get("mode") in ("single", "generate", "new-chain"):
        for sp in speakers:
            if not re.search(r"^\s*(?:%s['’]?S?\s+VOICE|VOICE[^\n]{0,40}%s)" % (re.escape(sp), re.escape(sp)), text, re.IGNORECASE | re.MULTILINE):
                errors.append("Speaker %s has no voice block. Add '%s'S VOICE:' with pitch, tone and delivery." % (sp, sp))
    if style == "full" and speakers and not re.search(r"\bSAME\b", text):
        warnings.append("No dialogue shot says 'in his/her SAME ... voice'.")

    # 9. extension and chain
    mode = segment.get("mode")
    if mode == "extend":
        if not re.search(r"\bextend", text[:700], re.IGNORECASE):
            errors.append("An extension prompt must start with 'Extend the @ TAG VIDEO from the exact final frame ...'.")
        if prev and prev.get("last_line"):
            if not _run_tokens(words(text.split("SHOT 1")[0]), words(prev["last_line"])):
                errors.append("The extension must quote the previous clip's last spoken line in the opening: “%s”" % prev["last_line"])
    if mode == "new-chain" and not re.search(r"(first[- ]frame|@\s?Image|last frame)", text[:900], re.IGNORECASE):
        warnings.append("A new chain should name the previous clip's last frame as the first-frame reference.")

    # 10. sound
    for line in text.splitlines():
        if re.search(r"\b(music|soundtrack|score|BGM)\b", line, re.IGNORECASE) and not re.search(r"\bNO\b|\bnever\b|\bwithout\b|\bonly\b", line, re.IGNORECASE):
            warnings.append("Mentions music outside a 'NO music' line: %s" % line.strip()[:70])
            break

    return {"errors": errors, "warnings": warnings, "timing": {k: v for k, v in timing.items() if k != "rows"}}
