#!/usr/bin/env python3
"""Split an episode script into clip-sized segments for Seedance generation.

Usage:
    python3 segment_episode.py episode.txt [--clip 15] [--chain 30] [--json]
    cat episode.txt | python3 segment_episode.py - --json

What it does
    1. Splits the script into scenes (scene headings: "SCENE 3", "INT.", "EXT.", "INT/EXT.").
    2. Turns each scene into timed events: spoken lines, action beats, sound cues.
    3. Fits every scene to the clip budget:
         up to --clip seconds          one generation                      (mode: single)
         up to --chain seconds         generation + one extension          (generate, extend)
         longer than --chain           several chains, each starting from the previous last frame
         shorter than --min-clip       merged into the next scene when they share a location,
                                       otherwise kept as a short clip
    4. Chooses cut points at the end of a spoken exchange, never in the middle of a line.

All times are estimates. Tune them with --wps, --line-gap, --action, --establish.

Accepted script formats (they can be mixed):
    NAME: spoken line               "ROXIE: Red light therapy."
    NAME (how)                      screenplay style, the speaker name on its own line in capitals,
    spoken line                     the next line is the dialogue
    quoted text inside an action    GIRL shouts: "BABE!"
    everything else                 action; each sentence is one beat
"""
import argparse
import json
import math
import re
import sys

TITLE_RE = re.compile(r"^\s*(?:EPISODE|TITLE|SERIES|SEASON)\b", re.IGNORECASE)
SCENE_RE = re.compile(r"^\s*(?:#+\s*|\*\*)?(SCENE\s*\d+\b.*|INT\.?/EXT\.?.*|I/E\.?.*|INT\..*|EXT\..*)$", re.IGNORECASE)
SPEAKER_COLON_RE = re.compile(r"^\s*([A-Z][A-Z0-9_.'\- ]{0,28}?)\s*(?:\(([^)]*)\))?\s*:\s*(\S.*)$")
NAME_QUOTE_RE = re.compile(r"^\s*([A-Z][A-Za-z0-9_.'\-]{1,20}(?: [A-Z][A-Za-z0-9_.'\-]{1,20})?)\s*(?:\(([^)]*)\))?\s*:\s*([“\"].*[”\"])\s*$")
CAPS_NAME_RE = re.compile(r"^\s*([A-Z][A-Z0-9_.'\-]*(?: [A-Z][A-Z0-9_.'\-]*){0,2})\s*(?:\(([^)]*)\))?\s*$")
QUOTE_RE = re.compile(r"[“\"]([^”\"\n]{1,300})[”\"]")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-]*")
TRANSITION_RE = re.compile(r"^\s*(?:HARD\s+CUT|IMMEDIATE\s+CUT|CUT\s+TO|CUT|FADE|DISSOLVE|SMASH|END\b|SHOT\s+\d+)", re.IGNORECASE)
PAUSE_RE = re.compile(r"\b(pause|beat|silence|freezes?|stares?|holds?)\b", re.IGNORECASE)
MOVING_RE = re.compile(r"\b(runs?|sprints?|jumps?|throws?|falls?|crash(?:es)?|dives?|punche?s?|leaps?|slams?|fires?)\b", re.IGNORECASE)
STOP_CAPS = {"INT", "EXT", "CUT", "TO", "HARD", "BLACK", "FADE", "IN", "OUT", "SHOT", "END", "DAY", "NIGHT", "SCENE",
             "THE", "AND", "OF", "NO", "NOT", "ONLY", "SAME", "NEVER", "DO", "ALL", "ON", "MUSIC", "POV", "DJI",
             "LED", "CONT", "VO", "OS", "IMPORTANT", "NOTE", "A", "I"}

SCENE_TYPE_HINTS = [
    ("action", r"\b(fight|chase|chases|chasing|run|runs|sprint|sprints|escape|explosion|fires|shoots|bullets|crash)\b"),
    ("revelation", r"\b(discovers?|reveals?|truth|realizes?|shock|twist|never reveals)\b"),
    ("suspense_horror", r"\b(stalk|spy|spying|watched|shadow|danger|creepy|eerie)\b"),
    ("farewell_ending", r"\b(goodbye|farewell|leaves|leaving|dies|death|last time)\b"),
    ("character_entrance", r"\b(walks in|enters|arrives|steps in|pushes the door)\b"),
    ("environment_establishing", r"\b(city|skyline|alley|street|bridge|waterfall|skyline|district)\b"),
    ("montage_transition", r"\b(montage|time passes|later that|days later|next morning)\b"),
]
MOOD_HINTS = [
    ("comedic", r"\b(joke|jokes|funny|bratty|deadpan|sarcastic|ridiculous|comedic|comedy)\b"),
    ("tense", r"\b(panic|panics|scream|screams|run|runs|sprint|sprints|bullet|bullets|drone|danger|afraid|fear)\b"),
    ("warm", r"\b(hug|hugs|smile|smiles|cozy|warm|kitten|gentle|soft)\b"),
    ("sad", r"\b(cry|cries|tears|alone|grief|lonely)\b"),
]


def norm_loc(heading):
    h = re.sub(r"^(?:SCENE\s*\d+\s*[-:—–.]*\s*)", "", heading.strip(), flags=re.IGNORECASE)
    h = re.sub(r"^(?:INT\.?/EXT\.?|I/E\.?|INT\.?|EXT\.?)\s*", "", h, flags=re.IGNORECASE)
    h = re.split(r"\s+[-—–]\s+", h)[0]
    return re.sub(r"[^A-Za-z0-9 ]", "", h).strip().lower()


def words(text):
    return len(WORD_RE.findall(text))


def parse_scenes(text):
    scenes, cur = [], None
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if TITLE_RE.match(line):
            continue
        m = SCENE_RE.match(line)
        if m and not QUOTE_RE.search(line):
            cur = {"heading": line.strip(" #*"), "lines": []}
            scenes.append(cur)
            continue
        if cur is None:
            if not line.strip():
                continue
            cur = {"heading": "(no heading)", "lines": []}
            scenes.append(cur)
        cur["lines"].append((ln, line))
    return scenes


def scene_events(lines, args):
    ev = []
    i = 0
    pending_caps = None
    items = [(n, l.strip()) for n, l in lines if l.strip()]
    while i < len(items):
        ln, line = items[i]
        i += 1
        if line.startswith("(") and line.endswith(")"):
            continue
        if re.fullmatch(r"[=\-_*~ ]{3,}", line):
            continue
        # NAME: "quoted"   or   NAME: text (all-caps name)
        m = NAME_QUOTE_RE.match(line) or SPEAKER_COLON_RE.match(line)
        if m and not TRANSITION_RE.match(line):
            speaker, how, spoken = m.group(1).strip(), m.group(2), m.group(3).strip()
            q = QUOTE_RE.findall(spoken)
            spoken = " ".join(q) if q else spoken
            ev.append(dialogue_event(speaker, how, spoken, ln, args))
            continue
        # screenplay style: caps name alone, dialogue on the next line
        c = CAPS_NAME_RE.match(line)
        if (c and not TRANSITION_RE.match(line) and not line.endswith(":") and not re.search(r"[.!?]$", line)
                and i < len(items) and not CAPS_NAME_RE.match(items[i][1]) and not SCENE_RE.match(items[i][1])
                and c.group(1).split()[0] not in STOP_CAPS):
            speaker, how = c.group(1).strip(), c.group(2)
            nl, nxt = items[i]
            i += 1
            q = QUOTE_RE.findall(nxt)
            ev.append(dialogue_event(speaker, how, " ".join(q) if q else nxt, nl, args))
            continue
        if TRANSITION_RE.match(line):
            ev.append({"kind": "transition", "speaker": None, "text": line, "words": 0, "seconds": 0.0, "line": ln})
            continue
        # action line, possibly with quoted dialogue inside
        quotes = QUOTE_RE.findall(line)
        if quotes:
            who = re.match(r"\s*([A-Z][A-Za-z0-9'\-]+)", line)
            ev.append(dialogue_event(who.group(1).upper() if who else "UNKNOWN", None, " ".join(quotes), ln, args))
            line = QUOTE_RE.sub("", line)
            if words(line) < 4:
                continue
        if re.fullmatch(r"[A-Z0-9 .!?,'\-]+", line) and re.search(r"[A-Z]{3,}[.!]", line):
            ev.append({"kind": "sfx", "speaker": None, "text": line, "words": 0, "seconds": args.sfx, "line": ln})
            continue
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", line) if WORD_RE.search(s)]
        for k, s in enumerate(sentences or [line]):
            extra = args.pause * len(PAUSE_RE.findall(s))
            base = args.action if k == 0 else args.detail   # extra sentences describe the same shot
            ev.append({"kind": "action", "speaker": None, "text": s.strip(), "words": 0,
                       "seconds": round(base + extra, 2), "line": ln, "first": k == 0})
    # an action line right before or after a spoken line is a reaction inside the dialogue shot
    for idx, e in enumerate(ev):
        if e["kind"] != "action" or not e.get("first"):
            continue
        near = (idx > 0 and ev[idx - 1]["kind"] == "dialogue") or (idx + 1 < len(ev) and ev[idx + 1]["kind"] == "dialogue")
        if near:
            extra = args.pause * len(PAUSE_RE.findall(e["text"]))
            e["seconds"] = round(args.reaction + extra, 2)
    return ev


def dialogue_event(speaker, how, spoken, ln, args):
    n = words(spoken)
    secs = n / args.wps + args.line_gap
    return {"kind": "dialogue", "speaker": speaker, "how": how, "text": spoken.strip(), "words": n,
            "seconds": round(secs, 2), "line": ln}


def total(events):
    return round(sum(e["seconds"] for e in events), 2)


def cut_score(prev, nxt):
    """Higher is a better place to end a clip and start the extension."""
    s = 0.0
    if prev["kind"] == "dialogue":
        s += 2.0
        if prev["text"].rstrip().endswith(("?", "!", "...", "\u2026")):
            s += 0.5
        if nxt is not None:
            if nxt["kind"] == "dialogue" and nxt["speaker"] == prev["speaker"]:
                s -= 3.0           # never cut inside one speaker's run
            elif nxt["kind"] == "dialogue":
                s += 0.5           # mid-exchange: the reply would open the extension
            else:
                s += 2.0           # the exchange is finished
    else:
        if MOVING_RE.search(prev["text"]):
            s -= 2.0               # a mid-motion frame is a poor extension start
    if nxt is not None and nxt["kind"] == "transition":
        s += 1.0
    return s


def split_events(events, clip, min_part):
    """Split the event list into consecutive parts, each at most `clip` seconds."""
    parts, rest = [], list(events)
    while total(rest) > clip + 1e-6:
        best, best_score, acc = None, -1e9, 0.0
        lower = max(min_part, total(rest) - clip * (math.ceil(total(rest) / clip) - 1))
        for i in range(1, len(rest)):
            acc = total(rest[:i])
            if acc > clip + 1e-6:
                break
            if acc < lower:
                continue
            sc = cut_score(rest[i - 1], rest[i]) + acc / clip * 0.5
            if sc > best_score:
                best, best_score = i, sc
        forced = False
        if best is None:
            forced = True
            acc, best = 0.0, 1
            for i in range(1, len(rest)):
                if total(rest[:i]) > clip + 1e-6:
                    break
                best = i
        parts.append((rest[:best], forced))
        rest = rest[best:]
    if rest:
        parts.append((rest, False))
    return parts


def hints(events, heading):
    blob = " ".join(e["text"] for e in events if e["kind"] != "dialogue") + " " + heading
    n_dlg = sum(1 for e in events if e["kind"] == "dialogue")
    scene_type = None
    for name, rx in SCENE_TYPE_HINTS:
        if re.search(rx, blob, re.IGNORECASE):
            scene_type = name
            break
    if scene_type is None:
        scene_type = "dialogue" if n_dlg >= 2 else ("static_or_insert" if n_dlg == 0 else "dialogue")
    if scene_type in ("action", "revelation") and n_dlg >= 4:
        scene_type = "dialogue" if scene_type != "action" else "action"
    mood = "neutral"
    alltext = blob + " " + " ".join(e["text"] for e in events if e["kind"] == "dialogue")
    for name, rx in MOOD_HINTS:
        if re.search(rx, alltext, re.IGNORECASE):
            mood = name
            break
    return scene_type, mood


def characters(scene_lines, events):
    names = {e["speaker"] for e in events if e["kind"] == "dialogue" and e["speaker"]}
    blob = " ".join(l for _, l in scene_lines)
    for tok in re.findall(r"\b[A-Z]{3,}\b", blob):
        if tok not in STOP_CAPS:
            names.add(tok)
    names.discard("UNKNOWN")
    return sorted(names)


def build(text, args):
    scenes = parse_scenes(text)
    out = []
    for si, sc in enumerate(scenes, 1):
        ev = scene_events(sc["lines"], args)
        establish = args.establish if sc["heading"] != "(no heading)" else 0.0
        if establish:
            ev.insert(0, {"kind": "establish", "speaker": None, "text": "establishing view of " + sc["heading"],
                          "words": 0, "seconds": establish, "line": 0})
        stype, mood = hints(ev, sc["heading"])
        out.append({"scene": si, "heading": sc["heading"], "location": norm_loc(sc["heading"]), "events": ev,
                    "seconds": total(ev), "characters": characters(sc["lines"], ev), "scene_type": stype, "mood": mood})
    # merge short scenes into the following scene when they share a location
    merged, i = [], 0
    while i < len(out):
        s = out[i]
        if (s["seconds"] < args.min_clip and i + 1 < len(out) and out[i + 1]["location"] == s["location"]
                and s["location"] and s["seconds"] + out[i + 1]["seconds"] <= args.clip):
            n = out[i + 1]
            s = {**n, "scene": s["scene"], "heading": s["heading"] + " + " + n["heading"], "events": s["events"] + n["events"],
                 "seconds": round(s["seconds"] + n["seconds"], 2), "characters": sorted(set(s["characters"]) | set(n["characters"])),
                 "merged_from": [s["scene"], n["scene"]]}
            i += 1
        merged.append(s)
        i += 1
    segments = []
    clip_eff = args.clip * (1 + args.tolerance)
    for s in merged:
        tot = s["seconds"]
        parts = [(s["events"], False)] if tot <= clip_eff else split_events(s["events"], clip_eff, args.min_part)
        clips_per_chain = max(1, int(args.chain // args.clip))
        for pi, (pev, forced) in enumerate(parts):
            est = total(pev)
            slot = pi % clips_per_chain
            if len(parts) == 1:
                mode = "single"
            elif slot == 0:
                mode = "generate" if pi == 0 else "new-chain"
            else:
                mode = "extend"
            nxt_ev = None
            if pi + 1 < len(parts):
                nxt_ev = next((e for e in parts[pi + 1][0] if e["kind"] != "transition"), None)
            last_ev = next((e for e in reversed(pev) if e["kind"] != "transition"), None)
            dlg = [e for e in pev if e["kind"] == "dialogue"]
            request = min(args.clip, max(args.min_gen, math.ceil(est * (1 + args.slack))))
            notes = []
            if est < args.min_clip and len(parts) == 1:
                notes.append("short clip: generate at %ds, or fold into a neighbouring scene as an insert if your tool needs a longer minimum" % request)
            if forced:
                notes.append("no clean cut point found; the cut falls inside a beat, check the extension frame")
            if args.clip < est <= clip_eff:
                notes.append("TIGHT: estimate %.1fs is over the %ds budget by %.1fs; trim a line or a beat, or accept the risk" % (est, args.clip, est - args.clip))
            elif est > clip_eff + 1e-6:
                notes.append("single event longer than the clip budget; shorten or split it by hand")
            if mode == "new-chain":
                notes.append("starts a new chain: use the last frame of the previous segment as the first-frame reference")
            if mode == "extend":
                notes.append("extension: start from the exact final frame of the previous segment")
            label = "S%02d" % s["scene"] + ("" if len(parts) == 1 else "abcdefghij"[pi])
            segments.append({
                "id": label, "scene": s["scene"], "heading": s["heading"], "location": s["location"],
                "mode": mode, "part": pi + 1, "parts": len(parts),
                "estimated_s": round(est, 1), "request_s": request,
                "dialogue_lines": len(dlg), "dialogue_words": sum(e["words"] for e in dlg),
                "characters": s["characters"], "scene_type_hint": s["scene_type"], "mood_hint": s["mood"],
                "last_beat": (last_ev["text"] if last_ev else ""), "last_beat_kind": (last_ev["kind"] if last_ev else ""),
                "next_beat": (nxt_ev["text"] if nxt_ev else ""),
                "events": [{k: e[k] for k in ("kind", "speaker", "text", "words", "seconds")} for e in pev if e["kind"] != "transition"],
                "notes": notes,
                "merged_from": s.get("merged_from"),
            })
    return segments


def render(segs, args):
    tot = sum(s["estimated_s"] for s in segs)
    lines = ["| Segment | Scene | Mode | Est. s | Request s | Lines | Words | Type / mood | Cut after |",
             "|---|---|---|---|---|---|---|---|---|"]
    for s in segs:
        cut = s["last_beat"]
        cut = (cut[:42] + "...") if len(cut) > 45 else cut
        lines.append("| %s | %s | %s | %.1f | %d | %d | %d | %s / %s | %s |" % (
            s["id"], s["heading"][:34], s["mode"], s["estimated_s"], s["request_s"], s["dialogue_lines"],
            s["dialogue_words"], s["scene_type_hint"], s["mood_hint"], cut if s["parts"] > 1 and s["part"] < s["parts"] else "(scene end)"))
    lines.append("")
    lines.append("Segments: %d   Estimated runtime: %.1fs (%.1f min)   Clip budget: %ds   Chain limit: %ds" % (
        len(segs), tot, tot / 60, args.clip, args.chain))
    for s in segs:
        for n in s["notes"]:
            lines.append("- %s: %s" % (s["id"], n))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="episode script, or - for stdin")
    ap.add_argument("--clip", type=float, default=15.0, help="seconds per generation (default 15)")
    ap.add_argument("--chain", type=float, default=30.0, help="longest generation + extensions chain (default 30)")
    ap.add_argument("--tolerance", type=float, default=0.07, help="estimates are good to about this fraction; a part up to clip*(1+tolerance) is kept and flagged TIGHT (default 0.07)")
    ap.add_argument("--min-clip", type=float, default=6.0, help="scenes shorter than this are merged or kept short (default 6)")
    ap.add_argument("--min-part", type=float, default=5.0, help="smallest piece produced by a split (default 5)")
    ap.add_argument("--min-gen", type=int, default=4, help="shortest generation you can request, assumed 4s")
    ap.add_argument("--slack", type=float, default=0.10, help="extra time added to the requested length (default 0.10)")
    ap.add_argument("--wps", type=float, default=3.4, help="spoken words per second (default 3.4, measured)")
    ap.add_argument("--line-gap", type=float, default=0.6, help="seconds added per spoken line for lead-in and reaction (default 0.6)")
    ap.add_argument("--action", type=float, default=2.0, help="seconds per action sentence (default 2.0)")
    ap.add_argument("--reaction", type=float, default=1.0, help="seconds for an action line next to a spoken line (default 1.0)")
    ap.add_argument("--detail", type=float, default=0.5, help="seconds for each extra sentence in the same action line (default 0.5)")
    ap.add_argument("--sfx", type=float, default=1.0, help="seconds per sound cue line (default 1.0)")
    ap.add_argument("--pause", type=float, default=0.5, help="extra seconds per pause/beat/hold word (default 0.5)")
    ap.add_argument("--establish", type=float, default=2.0, help="seconds for the establishing view at each scene heading (default 2.0)")
    ap.add_argument("--json", action="store_true", help="print JSON for agents")
    args = ap.parse_args()
    text = sys.stdin.read() if args.file == "-" else open(args.file, encoding="utf-8").read()
    segs = build(text, args)
    if args.json:
        print(json.dumps({"clip_s": args.clip, "chain_s": args.chain, "segments": segs}, indent=2, ensure_ascii=False))
    else:
        print(render(segs, args))


if __name__ == "__main__":
    main()
