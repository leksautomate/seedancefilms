#!/usr/bin/env python3
"""Count dialogue per shot in a Seedance prompt and estimate the running time.

Usage:
    python3 dialogue_timing.py prompt.txt [--max 15] [--wps 2.5]
    cat prompt.txt | python3 dialogue_timing.py - --max 15

The prompt is split on lines that start with "SHOT <n>". Text inside quotation
marks (straight or curly) inside a shot is counted as spoken dialogue. Anything
before SHOT 1 (the header, voice blocks, rules) is ignored.

Time model (all values are estimates, adjust with the flags):
    dialogue seconds = words / wps  +  lines * line_gap  +  pause_cost * pause notes
    shot seconds     = max(min_shot, dialogue seconds + pad)   when the shot has dialogue
                     = min_shot                                  when it has none
"""
import argparse
import json
import re
import sys

SHOT_RE = re.compile(r"^\s*(?:\*\*)?SHOT\s+(\d+)\b(.*)$", re.IGNORECASE | re.MULTILINE)
QUOTE_RE = re.compile(r"[“\"]([^”\"\n]{1,300})[”\"]")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-]*")
PAUSE_RE = re.compile(r"\b(pause|beat|hold|holds|silence)\b", re.IGNORECASE)
REFERENCE_LINE_RE = re.compile(r"\bafter\b.*\bsays?\b", re.IGNORECASE)
NO_DIALOGUE_RE = re.compile(r"\bno dialogue\b", re.IGNORECASE)
LONG_LINE_WORDS = 10


def split_shots(text):
    matches = list(SHOT_RE.finditer(text))
    if not matches:
        return [("1", "(whole prompt)", text)]
    shots = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        shots.append((m.group(1), m.group(2).strip(" —-:*"), text[m.end():end]))
    return shots


def dialogue_lines(block):
    """Return the lines a character actually speaks in this shot.

    A quoted string counts as dialogue when it sits on its own line or after a
    speaker label that ends with a colon ("ROXIE, casually: \"...\""). It is
    skipped when it is only mentioned inside a descriptive sentence, for example
    an expression ('a "what am I looking at?" expression') or a back-reference
    ('Brief pause before "NOW!"'), or when it repeats the previous clip's last
    line ("Continue after GIRL says: \"...\"").
    """
    lines = []
    skip_next_quote_line = False
    for raw in block.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if REFERENCE_LINE_RE.search(stripped):
            # the quoted line may sit on this line or on the next non-empty line
            skip_next_quote_line = not QUOTE_RE.search(stripped)
            continue
        quotes = QUOTE_RE.findall(stripped)
        if not quotes:
            skip_next_quote_line = False
            continue
        if skip_next_quote_line:
            skip_next_quote_line = False
            continue
        outside = QUOTE_RE.sub(" ", stripped)
        outside_words = len(WORD_RE.findall(outside))
        if outside_words > 3 and not outside.rstrip().endswith(":"):
            continue
        for q in quotes:
            if WORD_RE.search(q):
                lines.append(q.strip())
    return lines


def analyse(text, wps, line_gap, pause_cost, pad, min_shot):
    rows = []
    for number, title, block in split_shots(text):
        lines = dialogue_lines(block)
        words = sum(len(WORD_RE.findall(l)) for l in lines)
        pauses = 0 if NO_DIALOGUE_RE.search(block) else len(PAUSE_RE.findall(block))
        if lines:
            speak = words / wps + len(lines) * line_gap + pauses * pause_cost
            seconds = max(min_shot, speak + pad)
        else:
            speak = 0.0
            seconds = min_shot
        rows.append({
            "shot": number,
            "title": title,
            "lines": len(lines),
            "words": words,
            "speaking_s": round(speak, 1),
            "shot_s": round(seconds, 1),
            "texts": lines,
            "long_lines": [l for l in lines if len(WORD_RE.findall(l)) > LONG_LINE_WORDS],
        })
    return rows


def verdict(total, limit):
    if total <= limit * 0.9:
        return "FITS"
    if total <= limit:
        return "TIGHT"
    return "TOO LONG"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="prompt text file, or - for stdin")
    ap.add_argument("--max", type=float, default=15.0, help="clip length limit in seconds (default 15)")
    ap.add_argument("--wps", type=float, default=3.0, help="spoken words per second (default 3.0 for fast animated comedy; slow deadpan 2.5, dramatic 2.0)")
    ap.add_argument("--line-gap", type=float, default=0.2, help="seconds added per spoken line (default 0.2)")
    ap.add_argument("--pause", type=float, default=0.5, help="seconds per pause/beat/hold note (default 0.5)")
    ap.add_argument("--pad", type=float, default=0.3, help="entry/exit padding for a shot with dialogue (default 0.3)")
    ap.add_argument("--min-shot", type=float, default=1.2, help="shortest visible shot in seconds (default 1.2)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = ap.parse_args()

    text = sys.stdin.read() if args.file == "-" else open(args.file, encoding="utf-8").read()
    rows = analyse(text, args.wps, args.line_gap, args.pause, args.pad, args.min_shot)
    total_words = sum(r["words"] for r in rows)
    total_lines = sum(r["lines"] for r in rows)
    total_s = round(sum(r["shot_s"] for r in rows), 1)
    spoken_s = round(sum(r["speaking_s"] for r in rows), 1)
    result = verdict(total_s, args.max)

    if args.json:
        print(json.dumps({"shots": rows, "total_lines": total_lines, "total_words": total_words,
                          "speaking_s": spoken_s, "estimated_s": total_s, "limit_s": args.max,
                          "verdict": result}, indent=2, ensure_ascii=False))
        return

    print(f"{'Shot':<5}{'Lines':>6}{'Words':>7}{'Speak s':>9}{'Shot s':>8}  Dialogue")
    print("-" * 78)
    for r in rows:
        preview = " / ".join(r["texts"]) if r["texts"] else "-"
        if len(preview) > 40:
            preview = preview[:37] + "..."
        print(f"{r['shot']:<5}{r['lines']:>6}{r['words']:>7}{r['speaking_s']:>9}{r['shot_s']:>8}  {preview}")
    print("-" * 78)
    print(f"{'Total':<5}{total_lines:>6}{total_words:>7}{spoken_s:>9}{total_s:>8}")
    print()
    print(f"Estimated running time: {total_s}s   Limit: {args.max}s   Result: {result}")
    if result == "TOO LONG":
        over = total_s - args.max
        print(f"Over by about {over:.1f}s. Cut roughly {int(over * args.wps) + 1} spoken words, "
              f"shorten visual-only shots, or split into two clips (use the extend prompt).")
    elif result == "TIGHT":
        print("Within the limit but with little slack. Trim a line or a visual beat to be safe.")
    for r in rows:
        for l in r["long_lines"]:
            shown = l if len(l) <= 60 else l[:57] + "..."
            print(f"Note: shot {r['shot']} has a long line ({len(WORD_RE.findall(l))} words): \"{shown}\"")


if __name__ == "__main__":
    main()
