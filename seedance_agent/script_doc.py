"""Reads an annotated production script and turns it into clean input for the segmenter.

The format (one episode per paste) looks like this:

    MOVIE TITLE
    Episode 02: Episode Title
    Arc 1: The Fall | Runtime: 3:00 | Setting: ...

    CORE CHARACTERS IN THIS EPISODE        name (qualifier) - look. Voice.
    LOCATIONS IN THIS EPISODE              place, time - description
    RUNTIME MAP                            Block / Time / Length / Word budget (tab separated)

    [0:00-0:04] OPENING
    CLIP A (0:04-0:55)
    HOOK [0:04-0:22]                       or  SCENE 1: TITLE [0:22-0:55]
    Characters on screen: ...
    INT. PLACE, NIGHT. action ...          the location sits inside the first action paragraph
    NAME: (how) spoken line
    TEXT: on-screen text                   an edit overlay, not something the video model should draw
    END CARD [2:56-3:00]
    PRODUCTION NOTES

Everything that is not a scene (title block, character and location lists, runtime map, opening bumper, end card,
notes) is read into metadata. The scenes are rewritten as plain `SCENE n - INT. PLACE - TIME` blocks that the
segmenter understands. A script that does not follow this template returns None and is used as it is.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

TIME_WORDS = r"(?:NIGHT|DAY|MIDDAY|MIDNIGHT|NOON|MORNING|AFTERNOON|EVENING|DAWN|DUSK|SUNSET|SUNRISE|AUTUMN|WINTER|SPRING|SUMMER|LATER|CONTINUOUS)"
MONTHS = r"(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)"
TIME_PART = re.compile(r"^(?:%s\b.*|%s\b.*|\d{3,4}s?\b.*)$" % (TIME_WORDS, MONTHS), re.IGNORECASE)
LOC_SENTENCE = re.compile(r"\b(INT\.?/EXT\.?|EXT\.?/INT\.?|INT\.|EXT\.)\s+([^.\n]+?)\s*\.(?=\s|$)")
OVERLAY = re.compile(r"\bTEXT:\s*(.*?)(?=\s+(?:INT\.|EXT\.)|$)", re.IGNORECASE)
CUT_SENTENCE = re.compile(r"^(?:SMASH|HARD|MATCH|JUMP|QUICK)?\s*CUT(?:\s+TO(?:\s+BLACK)?)?\.?$", re.IGNORECASE)
MARKER = re.compile(r"^\s*(?:\[\d+:\d{2}\s*-\s*\d+:\d{2}\]|CLIP\s+[A-Z]\s*\(|HOOK\b|SCENE\s*\d+)", re.IGNORECASE)
TIMESPAN = re.compile(r"(\d+):(\d{2})\s*-\s*(\d+):(\d{2})")


def _secs(m, i=1) -> int:
    return int(m.group(i)) * 60 + int(m.group(i + 1))


@dataclass
class Scene:
    number: int
    title: str
    clip: str = ""
    planned_s: float | None = None
    on_screen: list[str] = field(default_factory=list)
    overlays: list[str] = field(default_factory=list)
    place: str = ""
    time: str = ""
    intext: str = ""
    lines: list[str] = field(default_factory=list)


@dataclass
class Doc:
    movie: str = ""
    episode_number: int | None = None
    episode_title: str = ""
    arc: str = ""
    runtime_s: int | None = None
    setting: str = ""
    characters: list[dict] = field(default_factory=list)
    locations: list[dict] = field(default_factory=list)
    blocks: list[dict] = field(default_factory=list)
    opening: str = ""
    end_card: str = ""
    notes: list[str] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)
    normalized: str = ""


def _split_top(text: str) -> list[str]:
    """Split on commas that are not inside brackets."""
    out, depth, cur = [], 0, ""
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def _characters(lines: list[str]) -> list[dict]:
    chars = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^extras?\s*:", line, re.IGNORECASE):
            for part in _split_top(re.sub(r"^extras?\s*:\s*", "", line, flags=re.IGNORECASE).rstrip(".")):
                m = re.match(r"^(.*?)\s*\((.*)\)\s*$", part)
                chars.append({"name": (m.group(1) if m else part).strip(), "qualifier": "extra", "look": m.group(2).strip() if m else "", "voice": "", "extra": True})
            continue
        pieces = re.split(r"\s[\u2014\u2013-]\s", line, maxsplit=1)
        left, right = pieces[0], (pieces[1] if len(pieces) > 1 else "")
        m = re.match(r"^(.*?)\s*\((.*)\)\s*$", left.strip())
        name = (m.group(1) if m else left).strip()
        qual = m.group(2).strip() if m else ""
        sentences = [s.strip() for s in re.split(r"(?<=\.)\s+", right.strip()) if s.strip()]
        voice = " ".join(s for s in sentences if re.search(r"\bvoice\b", s, re.IGNORECASE))
        look = " ".join(s for s in sentences if s not in voice)
        chars.append({"name": name, "qualifier": qual, "look": look.strip(), "voice": voice.strip(), "extra": False})
    return chars


def _locations(lines: list[str]) -> list[dict]:
    out = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        parts = re.split(r"\s[—–-]\s", line, maxsplit=1)
        place, time = _place_time([p.strip() for p in parts[0].split(",")])
        out.append({"name": place, "time": time, "description": parts[1].strip() if len(parts) > 1 else ""})
    return out


def _place_time(parts: list[str]) -> tuple[str, str]:
    for i, p in enumerate(parts):
        if i > 0 and TIME_PART.match(p.strip()):
            return ", ".join(parts[:i]), ", ".join(parts[i:])
    return ", ".join(parts), ""


def _blocks(lines: list[str]) -> list[dict]:
    rows = []
    for raw in lines:
        cells = [c.strip() for c in re.split(r"\t+|\s{2,}", raw.strip()) if c.strip()]
        if len(cells) < 3 or cells[0].lower() == "block":
            continue
        t = TIMESPAN.search(cells[1])
        words = re.search(r"\d+", cells[3]) if len(cells) > 3 else None
        length = re.search(r"\d+", cells[2])
        rows.append({"block": cells[0], "start_s": _secs(t) if t else None, "end_s": _secs(t, 3) if t else None,
                     "seconds": int(length.group(0)) if length else None, "words": int(words.group(0)) if words else 0})
    return rows


def looks_like_production_script(text: str) -> bool:
    return bool(re.search(r"^\s*RUNTIME MAP\s*$", text, re.IGNORECASE | re.MULTILINE)
                and re.search(r"^\s*CLIP\s+[A-Z]\s*\(", text, re.IGNORECASE | re.MULTILINE))


def parse(text: str) -> Doc | None:
    if not looks_like_production_script(text):
        return None
    lines = text.splitlines()
    idx = {}
    for i, l in enumerate(lines):
        u = l.strip().upper()
        if u.startswith("CORE CHARACTERS") and "chars" not in idx:
            idx["chars"] = i
        elif u.startswith("LOCATIONS") and "locs" not in idx:
            idx["locs"] = i
        elif u == "RUNTIME MAP" and "map" not in idx:
            idx["map"] = i
        elif u.startswith("PRODUCTION NOTES") and "notes" not in idx:
            idx["notes"] = i
        elif u.startswith("END CARD") and "end" not in idx and "map" in idx:
            idx["end"] = i
    n = len(lines)
    body_start = next((i for i in range(idx["map"] + 1, n) if MARKER.match(lines[i])), n)
    first_section = min([v for k, v in idx.items() if k in ("chars", "locs", "map")] or [n])
    doc = Doc()

    head = [l.strip() for l in lines[:first_section] if l.strip()]
    if head:
        doc.movie = head[0] if len(head) > 1 and re.match(r"^episode\b", head[1], re.IGNORECASE) else ""
    for l in head:
        m = re.match(r"^episode\s*(\d+)\s*[:\-–—]?\s*(.*)$", l, re.IGNORECASE)
        if m:
            doc.episode_number, doc.episode_title = int(m.group(1)), m.group(2).strip()
        if "|" in l:
            for part in l.split("|"):
                k, _, v = part.partition(":")
                k = k.strip().lower()
                if k == "runtime":
                    t = re.match(r"(\d+):(\d{2})", v.strip())
                    doc.runtime_s = int(t.group(1)) * 60 + int(t.group(2)) if t else None
                elif k == "setting":
                    doc.setting = v.strip()
                elif k.startswith("arc"):
                    doc.arc = part.strip()

    def section(start_key, stops):
        if start_key not in idx:
            return []
        end = min([idx[s] for s in stops if s in idx and idx[s] > idx[start_key]] + [body_start if start_key in ("chars", "locs", "map") else n])
        return lines[idx[start_key] + 1:end]

    doc.characters = _characters(section("chars", ["locs", "map"]))
    doc.locations = _locations(section("locs", ["map"]))
    doc.blocks = _blocks(section("map", []))

    body_end = min([idx[k] for k in ("end", "notes") if k in idx] + [n])
    if "end" in idx:
        end_stop = idx.get("notes", n)
        doc.end_card = " ".join(l.strip() for l in lines[idx["end"]:end_stop] if l.strip())
    if "notes" in idx:
        doc.notes = [l.strip() for l in lines[idx["notes"] + 1:] if l.strip()]

    # ---- the scenes ------------------------------------------------------
    clip_label, clip_span = "", None
    cur: Scene | None = None
    for raw in lines[body_start:body_end]:
        s = raw.strip()
        if not s:
            continue
        m = re.match(r"^\[(\d+:\d{2})\s*-\s*(\d+:\d{2})\]\s*(.*)$", s)
        if m and not cur:
            doc.opening = s
            continue
        m = re.match(r"^CLIP\s+([A-Z])\s*\((.*?)\)", s, re.IGNORECASE)
        if m:
            clip_label = m.group(1).upper()
            t = TIMESPAN.search(m.group(2))
            clip_span = (_secs(t), _secs(t, 3)) if t else None
            continue
        m = re.match(r"^HOOK\b\s*(?:\[(.*?)\])?", s, re.IGNORECASE)
        sc = re.match(r"^SCENE\s*(\d+)\s*[:.\-–—]?\s*(.*?)\s*(?:\[(.*?)\])?\s*$", s, re.IGNORECASE)
        if m or sc:
            if m:
                number, title, span = 0, "Hook", m.group(1)
            else:
                number, title, span = int(sc.group(1)), sc.group(2).strip(), sc.group(3)
            cur = Scene(number=number, title=title.title() if title.isupper() else title, clip=clip_label)
            t = TIMESPAN.search(span or "")
            if t:
                cur.planned_s = _secs(t, 3) - _secs(t)
            elif clip_span:
                cur.planned_s = clip_span[1] - clip_span[0]
            doc.scenes.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^characters on screen\s*:\s*(.*)$", s, re.IGNORECASE)
        if m:
            cur.on_screen = _split_top(m.group(1).rstrip("."))
            continue
        cur.lines.append(s)

    for sc in doc.scenes:
        _normalise_scene(sc)
    doc.normalized = _render(doc)
    return doc


def _normalise_scene(sc: Scene) -> None:
    """Pull the location and on-screen text out of the first action paragraph; drop bare cut instructions."""
    out = []
    taken_loc = False
    for line in sc.lines:
        # dialogue lines are kept exactly
        if re.match(r"^[A-Z][A-Z0-9 .'\-]{1,28}(?:\s*\([^)]*\))?\s*:\s*\S", line) and not line.upper().startswith(("TEXT:", "INT.", "EXT.")):
            out.append(line)
            continue
        work = line
        for m in OVERLAY.finditer(work):
            sc.overlays.append(m.group(1).strip())
        work = OVERLAY.sub("", work).strip()
        if not taken_loc:
            m = LOC_SENTENCE.search(work)
            if m:
                place, time = _place_time([p.strip() for p in m.group(2).split(",")])
                sc.place, sc.time, sc.intext = place, time, m.group(1).upper().replace("INT/EXT", "INT./EXT.")
                work = (work[:m.start()] + " " + work[m.end():]).strip()
                taken_loc = True
        sentences = [x for x in re.split(r"(?<=[.!?])\s+", work) if x.strip() and not CUT_SENTENCE.match(x.strip())]
        if re.fullmatch(r"(?:SMASH|HARD|MATCH)?\s*CUT TO BLACK\.?", work.strip(), re.IGNORECASE):
            out.append("CUT TO BLACK.")
            continue
        if sentences:
            out.append(" ".join(sentences))
    sc.lines = out


def _render(doc: Doc) -> str:
    parts = []
    for sc in doc.scenes:
        place = sc.place.upper() if sc.place else sc.title.upper()
        time = (" - " + sc.time.upper()) if sc.time else ""
        parts.append("SCENE %d - %s %s%s" % (sc.number, sc.intext or "INT.", place, time))
        parts.extend(sc.lines)
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def match_location(doc: Doc, place: str) -> str:
    """The scene's place, spelled as the LOCATIONS list spells it ("Qutuz's tent, Salihiyya camp")."""
    key = re.sub(r"[^a-z0-9]", "", place.lower())
    for loc in doc.locations:
        lk = re.sub(r"[^a-z0-9]", "", loc["name"].lower())
        if key and (key == lk or key in lk or lk in key):
            return loc["name"]
    return place.strip().capitalize() if place.isupper() else place.strip()


def tag_for_place(place: str) -> str:
    first = place.split(",")[0].strip()
    return "@ TAG %s" % re.sub(r"['’]s\b", "", first).upper()


def bible_seed(doc: Doc, speakers: list[str]) -> dict:
    """Match each speaker name in the script to a character in the CORE CHARACTERS list."""
    def toks(s: str) -> list[str]:
        return re.findall(r"[a-z0-9\-]+", s.lower())

    seed: dict = {}
    for sp in speakers:
        stoks = toks(sp)
        young = bool(stoks and stoks[0] in ("young", "little", "boy", "girl"))
        core = stoks[1:] if young else stoks
        cands = []
        for c in doc.characters:
            ntoks = toks(c["name"])
            if core and all(t in ntoks for t in core):
                q = c["qualifier"].lower()
                is_child = any(w in q for w in ("child", "young", "boy", "girl", "kid"))
                cands.append((0 if (young == is_child) else 1, len(ntoks), c))
        if cands:
            cands.sort(key=lambda x: (x[0], x[1]))
            c = cands[0][2]
            seed[sp] = {"look": c["look"], "voice": c["voice"], "source": "script"}
    return seed
