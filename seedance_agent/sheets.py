"""Character and location continuity sheets: the prompts for the reference images, and voice design prompts.

This follows the studio's character-location-extractor-builder skill:
  - the script is the only source of truth; anything added is marked "(proposed)"
  - one character per prompt, one location per prompt, one look per character
  - a 16:9 landscape continuity sheet in the chosen style (white studio background for characters)
  - a voice design prompt only for a character who appears in more than one scene, or who leads the series
  - files are named with the @ tag in PascalCase (@Qutuz, @CitadelThroneRoom), the same name the image gets later

The model supplies structured fields. Code renders the template from them, so the structure never drifts and no
placeholder is left behind. A sheet that fails the checks is not saved as ready.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .agent import Tool
from .tools import AskBudget, ask_user_tool

STYLE_EXAMPLES = ["Photorealistic cinematic", "Anime / manga", "3D animated (Pixar-like)", "2D illustrated / storybook",
                  "Graphic novel / comic", "Dark documentary / painterly"]
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
EFFECT_WORDS = re.compile(r"\b(reverb|echo|phone|telephone|radio|distort\w*|filter\w*|robot\w*)\b", re.IGNORECASE)

CHAR_REQUIRED = ["name", "tag", "role", "age", "height", "body_type", "personality", "traits", "signature_colors", "face_details",
                 "costume_details", "posture_notes", "materials", "lock", "close_up"]
LOC_REQUIRED = ["name", "tag", "role", "setting_type", "era", "region", "scale", "mood", "signature_colors", "layout", "angle_notes",
                "key_zones", "lighting_variants", "materials", "lock"]


def pascal(name: str) -> str:
    """'Qutuz's tent' -> '@QutuzsTent'. Words are split on spaces and punctuation."""
    words = re.findall(r"[A-Za-z0-9]+", re.sub(r"['’]s\b", "s", name))
    return "@" + "".join(w[:1].upper() + w[1:] for w in words)


def _clean(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _s(x) -> str:
    """Text for the end of a sentence: no trailing full stop, so the template can add its own."""
    return _clean(x).rstrip(". ")


def _material_phrase(style: str) -> str:
    return "realistic materials" if re.search(r"photo|realistic|live[- ]action", style, re.IGNORECASE) else "stylized materials consistent with the chosen style"


def _palette_text(palette) -> str:
    return "; ".join("%s %s" % (_clean(p.get("label")), _clean(p.get("hex")).upper()) for p in palette or [] if isinstance(p, dict))


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def render_character_prompt(e: dict, style: str) -> str:
    g = lambda k: _clean(e.get(k))
    alias = (" (also called %s)" % g("alias")) if g("alias") else ""
    notes = "; ".join(_clean(n) for n in e.get("notes", []) if _clean(n))
    parts = [
        "Create a polished 16:9 landscape continuity sheet focused exclusively on the character, rendered in %s:" % style,
        "1. CHARACTER PROFILE — %s%s. Role: %s. %s, %s, %s build. Personality: %s. Distinctive traits: %s. Signature colors: %s." % (
            g("name"), alias, _s(e.get("role")), g("age"), g("height"), g("body_type"), _s(e.get("personality")), _s(e.get("traits")), _s(e.get("signature_colors"))),
        "2. FULL-BODY TURNAROUND — front, 3/4, side, and back views of the exact same character at matching scale, with identical facial features, "
        "hairstyle, body proportions, costume, colors, and accessories, standing in a neutral pose beside a vertical height scale in centimeters. %s" % g("turnaround") if g("turnaround") else
        "2. FULL-BODY TURNAROUND — front, 3/4, side, and back views of the exact same character at matching scale, with identical facial features, "
        "hairstyle, body proportions, costume, colors, and accessories, standing in a neutral pose beside a vertical height scale in centimeters. Outfit: %s." % g("outfit_summary"),
        "3. FACE AND IDENTITY DETAILS — front, profile, and 3/4 head-and-shoulder close-ups showing facial structure, eyes, eyebrows, nose, lips, hairstyle, "
        "skin tone, makeup, scars, tattoos, and other defining features. %s" % g("face_details"),
        "4. EXPRESSION SHEET — neutral, happy, angry, sad, surprised, worried, confident, and determined expressions. Preserve the exact same facial "
        "structure and identity in every expression.%s" % ((" " + g("expression_notes")) if g("expression_notes") else ""),
        "5. POSE AND BODY LANGUAGE — neutral standing, walking, sitting, relaxed, tense, and action-ready poses. Maintain consistent anatomy, proportions, "
        "posture, and silhouette. %s" % g("posture_notes"),
        "6. COSTUME DETAILS — close-ups of clothing layers, fabrics, seams, fasteners, footwear, jewelry, eyewear, markings, and other character-defining "
        "wardrobe elements. %s" % g("costume_details"),
        "7. COLOR AND MATERIAL PALETTE — key colors with HEX codes: %s. Materials: %s." % (_palette_text(e.get("palette")), _s(e.get("materials"))),
        "8. DO NOT CHANGE — lock the character's face, identity, skin tone, age, hair, eye color, body shape, proportions, costume, accessories, markings, "
        "colors, and defining features: %s. Do not redesign, beautify, age, stylize, simplify, or create alternate versions." % _s(e.get("lock")),
        "Use a plain solid white studio background (always white, no gradients or scenery), soft controlled lighting, %s, sharp details, subtle shadows, "
        "clean typography, thin dividers, balanced spacing, and a sophisticated editorial production-design grid laid out horizontally across the wide frame."
        % _material_phrase(style),
        ("Include a small NOTES PANEL with annotation text (%s) and one cinematic CLOSE-UP POSE of the character: %s." % (notes, _s(e.get("close_up")))) if notes else
        ("Include one cinematic CLOSE-UP POSE of the character: %s." % _s(e.get("close_up"))),
        "Every panel must depict the exact same character with absolute visual consistency. Focus only on the character. Do not include props, additional "
        "characters, environments, unrelated objects, or alternate outfits.",
    ]
    return "\n".join(parts)


def render_location_prompt(e: dict, style: str) -> str:
    g = lambda k: _clean(e.get(k))
    notes = "; ".join(_clean(n) for n in e.get("notes", []) if _clean(n))
    parts = [
        "Create a polished 16:9 landscape continuity sheet focused exclusively on the location, rendered in %s:" % style,
        "1. LOCATION PROFILE — %s. Role in the story: %s. %s setting, %s, %s. Scale: %s. Mood: %s. Signature colors: %s." % (
            g("name"), _s(e.get("role")), g("setting_type").capitalize(), g("era"), g("region"), _s(e.get("scale")), _s(e.get("mood")), _s(e.get("signature_colors"))),
        "2. MASTER ESTABLISHING VIEW — one wide hero view showing the full space with accurate layout, architecture, and atmosphere. %s" % g("layout"),
        "3. MULTI-ANGLE VIEWS — front, left, right, and rear or reverse views of the same space, with matching scale, layout, and architectural details. %s" % g("angle_notes"),
        "4. KEY ZONES AND DETAILS — close-ups of the most important areas, entrances, windows, doors, floors, walls, ceilings, and other defining "
        "architectural elements: %s." % _s(e.get("key_zones")),
        "5. LIGHTING AND TIME OF DAY — the same location in the lighting the story calls for, with identical geometry in every version: %s." % _s(e.get("lighting_variants")),
        "6. MATERIAL AND TEXTURE REFERENCES — clean swatches or close-ups of the visible surfaces: %s." % _s(e.get("materials")),
        "7. COLOR PALETTE — key colors with HEX codes: %s, plus references for light color and shadow tone." % _palette_text(e.get("palette")),
        "8. DO NOT CHANGE — lock the layout, proportions, architecture, materials, colors, signature features, and atmosphere: %s. Do not redesign, "
        "modernize, beautify, simplify, or create alternate versions." % _s(e.get("lock")),
        "Use soft controlled lighting, sharp details, clean typography, thin dividers, balanced spacing, and a sophisticated editorial production-design grid."
        + ((" Include a small NOTES PANEL with annotation text (%s)." % notes) if notes else ""),
        "Every panel must depict the exact same location with absolute visual consistency. Focus only on the location. Do not include people, characters, "
        "vehicles, or unrelated objects.",
    ]
    return "\n".join(parts)


def render_voice(e: dict) -> str:
    v = e.get("voice") or {}
    if not v:
        return ""
    line = "VOICE DESIGN PROMPT: %s. %s. Studio quality. Persona: %s. Emotion: %s. %s" % (
        _clean(v.get("language_accent")).rstrip("."), _clean(v.get("gender_age")).rstrip("."), _clean(v.get("persona")).rstrip("."),
        _clean(v.get("emotion")).rstrip("."), _clean(v.get("delivery")))
    out = line.strip()
    if _clean(v.get("preview_text")):
        out += "\n\nPREVIEW TEXT: %s" % _clean(v["preview_text"])
    return out


def character_file(e: dict, style: str) -> str:
    text = e["tag"] + "\n\n" + render_character_prompt(e, style)
    voice = render_voice(e)
    return text + ("\n\n" + voice if voice else "") + "\n"


def location_file(e: dict, style: str) -> str:
    return e["tag"] + "\n\n" + render_location_prompt(e, style) + "\n"


def lists_md(chars: list[dict], locs: list[dict], style: str, extras: list[dict] | None = None) -> str:
    """Step 3 of the skill: the lists, shown before the prompts, with anything not in the script marked (proposed)."""
    out = ["# Core characters and locations", "", "Style: **%s**. Anything marked (proposed) is not in the script. Correct, add or remove anything, then run again." % style, "",
           "## Core characters", ""]
    for e in chars:
        g = lambda k: _clean(e.get(k)) or "-"
        out += ["### %s  `%s`" % (g("name"), e.get("tag", "")), "",
                "CHARACTER CORE:", "- Name: %s" % g("name"), "- Alias: %s" % g("alias"), "- Gender: %s" % g("gender"), "- Age: %s" % g("age"),
                "- Height: %s" % g("height"), "- Body Type: %s" % g("body_type"), "- Ethnicity: %s" % g("ethnicity"), "- Role: %s" % g("role"),
                "- Archetype: %s" % g("archetype"), "",
                "PERSONALITY & TRAITS:", "- Personality: %s" % g("personality"), "- Core Theme: %s" % g("core_theme"), "- Emotional Range: %s" % g("emotional_range"),
                "- Behavior Notes: %s" % g("behavior_notes"), "- Speech Style / Accent: %s" % g("speech_style"), "",
                "COLOR PALETTE:", "- %s" % (_palette_text(e.get("palette")) or "-"), "",
                "WARDROBE / ACCESSORIES:", "- Top: %s" % g("top"), "- Bottom: %s" % g("bottom"), "- Shoes: %s" % g("shoes"), "- Accessories: %s" % g("accessories"),
                "- Appears in scenes: %s" % (", ".join(str(s) for s in e.get("scenes", [])) or "-"),
                "- Voice design prompt: %s" % ("yes (appears in more than one scene or leads the series)" if e.get("voice") else "no"), ""]
    if extras:
        out += ["### Extras (no sheet; described in full inside every scene prompt)", ""]
        for x in extras:
            out.append("- %s: %s" % (_clean(x.get("name")), _clean(x.get("look")) or "(describe from the script)"))
        out.append("")
    out += ["## Core locations", ""]
    for e in locs:
        g = lambda k: _clean(e.get(k)) or "-"
        out += ["### %s  `%s`" % (g("name"), e.get("tag", "")), "", "- Role in the story: %s" % g("role"),
                "- Time of day / era / mood: %s; %s; %s" % (g("lighting_variants"), g("era"), g("mood")),
                "- Key visual details: %s" % g("key_zones"), "- Appears in scenes: %s" % (", ".join(str(s) for s in e.get("scenes", [])) or "-"), ""]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------
def _names_in(text: str, names: list[str]) -> list[str]:
    hits = []
    for n in names:
        if n and re.search(r"\b%s\b" % re.escape(n), text, re.IGNORECASE):
            hits.append(n)
    return hits


def _name_tokens(name: str) -> list[str]:
    return [t for t in re.findall(r"[A-Za-z\-]+", name) if len(t) >= 4 and t.lower() not in ("adult", "child", "young", "sultan", "elder", "slave", "emir")]


def lint_character(e: dict, prompt: str, style: str, others: list[dict], speech_lines: list[str], recurring: bool) -> dict:
    errors, warnings = [], []
    miss = [k for k in CHAR_REQUIRED if not _clean(e.get(k))]
    if miss:
        errors.append("Missing field(s): %s." % ", ".join(miss))
    if not re.fullmatch(r"@[A-Z][A-Za-z0-9]*", _clean(e.get("tag"))):
        errors.append("The tag must be PascalCase with no spaces, like @Qutuz.")
    pal = [p for p in e.get("palette", []) if isinstance(p, dict) and HEX.fullmatch(_clean(p.get("hex")))]
    if len(pal) < 4:
        errors.append("The palette needs 4 to 6 colors with real HEX codes like #7A1F1F (found %d)." % len(pal))
    if re.search(r"[{}<>]|\[[^\]]*\]", prompt):
        errors.append("The prompt contains a placeholder or bracket.")
    own = set(t.lower() for t in _name_tokens(e.get("name", "")))
    other_names = []
    for o in others:
        toks = _name_tokens(o.get("name", ""))
        if toks and not (own & set(t.lower() for t in toks)):
            other_names.append(toks[0])
    hit = _names_in(prompt, other_names)
    if hit:
        errors.append("One character per prompt: the prompt names %s." % ", ".join(hit))
    if style.lower() not in prompt.lower():
        errors.append("The chosen style is missing from the prompt.")
    if not re.search(r"\(proposed\)", json.dumps(e, ensure_ascii=False), re.IGNORECASE) and not e.get("fully_from_script"):
        warnings.append("Nothing is marked (proposed). If every detail is in the script, set fully_from_script to true.")
    v = e.get("voice")
    if recurring and not v:
        errors.append("This character appears in more than one scene or leads the series, so it needs a voice design prompt.")
    if v and not recurring:
        errors.append("A character who speaks in a single scene gets no voice design prompt.")
    if v:
        txt = render_voice(e)
        if EFFECT_WORDS.search(txt):
            errors.append("The voice design prompt uses an effect word (reverb, echo, phone...). Describe the voice only.")
        if not re.match(r"VOICE DESIGN PROMPT:\s*(English|American|British|Arabic|[A-Z][a-z]+)\b", txt):
            errors.append("The voice design prompt must name the language and regional variant first.")
        if re.search(r"\baccent\b", _clean(v.get("language_accent")), re.IGNORECASE) and not re.search(r"\b(slight|thick)\b", _clean(v.get("language_accent")), re.IGNORECASE):
            errors.append("Say 'slight' or 'thick' accent, never a bare 'accent'.")
        pv = _clean(v.get("preview_text"))
        if len(pv) < 100:
            errors.append("The preview text must be at least 100 characters of the character's own script lines.")
        else:
            script = " ".join(_clean(x) for x in speech_lines)
            norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower())
            sents = [s for s in re.split(r"(?<=[.!?])\s+", pv) if s.strip()]
            bad = [s for s in sents if norm(s) and norm(s) not in norm(script)]
            if bad:
                errors.append("The preview text must use the character's own lines word for word. Not found in the script: %s" % bad[0])
    return {"errors": errors, "warnings": warnings}


def lint_location(e: dict, prompt: str, style: str, characters: list[dict]) -> dict:
    errors, warnings = [], []
    miss = [k for k in LOC_REQUIRED if not _clean(e.get(k))]
    if miss:
        errors.append("Missing field(s): %s." % ", ".join(miss))
    if not re.fullmatch(r"@[A-Z][A-Za-z0-9]*", _clean(e.get("tag"))):
        errors.append("The tag must be PascalCase with no spaces, like @CitadelThroneRoom.")
    pal = [p for p in e.get("palette", []) if isinstance(p, dict) and HEX.fullmatch(_clean(p.get("hex")))]
    if len(pal) < 4:
        errors.append("The palette needs 4 to 6 colors with real HEX codes (found %d)." % len(pal))
    if re.search(r"[{}<>]|\[[^\]]*\]", prompt):
        errors.append("The prompt contains a placeholder or bracket.")
    names = [t for c in characters for t in _name_tokens(c.get("name", ""))[:1]]
    hit = _names_in(prompt, names)
    if hit:
        errors.append("A location sheet has no people: the prompt names %s." % ", ".join(hit))
    if style.lower() not in prompt.lower():
        errors.append("The chosen style is missing from the prompt.")
    return {"errors": errors, "warnings": warnings}


# ---------------------------------------------------------------------------
# the model's job: one item at a time, through a gated tool
# ---------------------------------------------------------------------------
PALETTE = {"type": "array", "items": {"type": "object", "properties": {"label": {"type": "string"}, "hex": {"type": "string", "description": "#RRGGBB"}}, "required": ["label", "hex"]}}
STR = {"type": "string"}
CHAR_PROPS = {k: STR for k in ("name", "tag", "alias", "gender", "age", "height", "body_type", "ethnicity", "role", "archetype", "personality", "core_theme",
                               "emotional_range", "behavior_notes", "speech_style", "traits", "signature_colors", "outfit_summary", "turnaround", "face_details",
                               "expression_notes", "posture_notes", "costume_details", "top", "bottom", "shoes", "accessories", "materials", "lock", "close_up")}
CHAR_PROPS.update({"palette": PALETTE, "notes": {"type": "array", "items": STR}, "proposed": {"type": "array", "items": STR},
                   "fully_from_script": {"type": "boolean"}, "speakers": {"type": "array", "items": STR},
                   "voice": {"type": "object", "properties": {k: STR for k in ("language_accent", "gender_age", "persona", "emotion", "delivery", "preview_text")}}})
LOC_PROPS = {k: STR for k in ("name", "tag", "role", "setting_type", "era", "region", "scale", "mood", "signature_colors", "layout", "angle_notes",
                              "key_zones", "lighting_variants", "materials", "lock")}
LOC_PROPS.update({"palette": PALETTE, "notes": {"type": "array", "items": STR}, "proposed": {"type": "array", "items": STR}})


@dataclass
class SheetJob:
    kind: str                       # "character" or "location"
    style: str
    others: list = field(default_factory=list)      # the other characters' entries (for the one-character rule)
    characters: list = field(default_factory=list)  # all characters (for the no-people rule on locations)
    speech_lines: list = field(default_factory=list)
    recurring: bool = False
    max_attempts: int = 3
    attempts: int = 0
    accepted: dict | None = None
    best: dict | None = None

    def submit(self, entry: dict) -> dict:
        e = dict(entry)
        e["notes"] = [n for n in e.get("notes", []) if isinstance(n, str)] if isinstance(e.get("notes"), list) else []
        e["palette"] = [p for p in e.get("palette", []) if isinstance(p, dict)] if isinstance(e.get("palette"), list) else []
        if self.kind == "character":
            prompt = render_character_prompt(e, self.style)
            report = lint_character(e, prompt, self.style, self.others, self.speech_lines, self.recurring)
        else:
            prompt = render_location_prompt(e, self.style)
            report = lint_location(e, prompt, self.style, self.characters)
        self.attempts += 1
        rec = {"entry": e, "prompt": prompt, "errors": report["errors"], "warnings": report["warnings"]}
        if self.best is None or len(rec["errors"]) < len(self.best["errors"]):
            self.best = rec
        if not report["errors"]:
            rec["status"] = "ok"
            self.accepted = rec
        elif self.attempts >= self.max_attempts:
            self.accepted = dict(self.best, status="needs-review")
        return {"accepted": self.accepted is not None, "status": (self.accepted or {}).get("status", "rejected"), "errors": report["errors"],
                "warnings": report["warnings"], "attempts_left": max(0, self.max_attempts - self.attempts)}


def sheet_tools(job: SheetJob, console, budget: AskBudget) -> list[Tool]:
    props = CHAR_PROPS if job.kind == "character" else LOC_PROPS
    req = CHAR_REQUIRED if job.kind == "character" else LOC_REQUIRED
    return [
        Tool("submit_sheet", "Submit the structured fields for this %s sheet. The prompt is rendered from them. If it has errors, fix them and submit again." % job.kind,
             {"type": "object", "properties": props, "required": req + ["palette"]}, lambda a: json.dumps(job.submit(a), ensure_ascii=False)),
        ask_user_tool(console, budget),
    ]
