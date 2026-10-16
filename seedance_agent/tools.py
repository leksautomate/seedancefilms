"""The tools the agent can call, and the gates behind them."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import lint as linter
from .agent import Tool
from .console import Console
from .skills_bridge import SKILLS

ENGINE = SKILLS / "cinematic-camera-engine" / "references"

SCENE_TYPES = ["dialogue", "action", "inner_monologue", "character_entrance", "environment_establishing",
               "character_introduction", "farewell_ending", "revelation", "static_emotion", "ensemble_climax",
               "montage_transition", "suspense_horror"]
RECIPE_NUMBER = {name: i + 1 for i, name in enumerate(SCENE_TYPES)}
RECIPE_NUMBER["static_or_insert"] = RECIPE_NUMBER["static_emotion"]
FLOW_NAMES = ["progressive_reveal", "emotional_focus", "shocking_reveal", "standard_dialogue", "escalating_dialogue",
              "action_sequence", "loneliness_departure", "ensemble_climax"]


def camera_lookup(scene_type: str, mood: str = "") -> str:
    """The camera engine's recipe for a scene type, plus the matching shot-flow template."""
    n = RECIPE_NUMBER.get((scene_type or "").strip().lower().replace(" ", "_").replace("-", "_"))
    if not n:
        return "Unknown scene_type %r. Use one of: %s" % (scene_type, ", ".join(SCENE_TYPES))
    recipes = (ENGINE / "scene-camera-recipes.md").read_text(encoding="utf-8")
    sections = re.split(r"\n(?=## \d+\. )", recipes)
    recipe = next((s for s in sections if s.startswith("## %d. " % n)), "")
    recipe = re.split(r"\n---\s*\n", recipe)[0].strip()
    flow_for = {"dialogue": "Template 4", "action": "Template 6", "inner_monologue": "Template 2", "character_entrance": "Template 1",
                "environment_establishing": "Template 1", "character_introduction": "Template 1", "farewell_ending": "Template 7",
                "revelation": "Template 3", "static_emotion": "Template 2", "ensemble_climax": "Template 8",
                "montage_transition": "Template 8", "suspense_horror": "Template 3", "static_or_insert": "Template 2"}
    key = (scene_type or "").strip().lower().replace(" ", "_")
    flow_head = flow_for.get(key, "Template 4")
    flows = (ENGINE / "shot-flow-patterns.md").read_text(encoding="utf-8")
    fsec = next((s for s in re.split(r"\n(?=## Template \d)", flows) if s.startswith("## " + flow_head)), "")
    fsec = re.split(r"\n### Rhythm parameters", fsec)[0].strip()
    out = "SCENE RECIPE\n\n%s\n\nSHOT FLOW\n\n%s" % (recipe, fsec)
    if mood:
        out = "Mood requested: %s. Pick the matching row in the mood variants.\n\n" % mood + out
    return out[:6000]


@dataclass
class AskBudget:
    left: int = 1


def ask_user_tool(console: Console, budget: AskBudget) -> Tool:
    def handler(args: dict) -> str:
        if budget.left <= 0:
            return "Question limit reached. Proceed on a stated assumption and list it under assumptions."
        if not console.interactive:
            return "NO_USER_AVAILABLE. Proceed on a stated assumption and list it under assumptions."
        budget.left -= 1
        ans = console.ask(str(args["question"]), args.get("options") or None)
        return ans or "(no answer given; proceed on a stated assumption)"
    return Tool("ask_user", "Ask the person one short question when a missing fact would change the result and you cannot make a safe "
                "assumption. Use sparingly: at most once per task.",
                {"type": "object", "properties": {"question": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}},
                 "required": ["question"]}, handler)


def lookup_tool() -> Tool:
    return Tool("lookup_camera_recipe", "Get the cinematic camera engine's recipe and shot-flow template for a scene type.",
                {"type": "object", "properties": {"scene_type": {"type": "string", "enum": SCENE_TYPES + ["static_or_insert"]},
                                                  "mood": {"type": "string"}}, "required": ["scene_type"]},
                lambda a: camera_lookup(a["scene_type"], a.get("mood", "")))


# ---------------------------------------------------------------------------
# one clip
# ---------------------------------------------------------------------------
@dataclass
class SegmentJob:
    segment: dict
    bible: dict
    settings: dict
    style: str = "full"
    prev: dict | None = None
    max_attempts: int = 4
    attempts: int = 0
    accepted: dict | None = None
    best: dict | None = None
    log: list = field(default_factory=list)

    def check(self, prompt: str) -> dict:
        return linter.lint(prompt, self.segment, self.bible, self.settings, self.style, self.prev)

    def _normalise(self, a: dict) -> dict:
        brief = a.get("brief") if isinstance(a.get("brief"), dict) else {}
        carry = a.get("carry_over") if isinstance(a.get("carry_over"), dict) else {}
        lst = lambda v: [str(x) for x in v] if isinstance(v, list) else ([str(v)] if v else [])
        events = [e for e in self.segment.get("events", []) if e.get("kind") == "dialogue"]
        return {
            "prompt": str(a["prompt"]).strip() + "\n",
            "shots": [x for x in a.get("shots", []) if isinstance(x, dict)] if isinstance(a.get("shots"), list) else [],
            "brief": {"purpose": str(brief.get("purpose", "")), "subject": str(brief.get("subject", "")),
                      "subject_action": str(brief.get("subject_action", "")), "camera": str(brief.get("camera", "locked-off framing with hard cuts")),
                      "environment": str(brief.get("environment", "")), "lighting": str(brief.get("lighting", "")),
                      "visual_direction": str(brief.get("visual_direction", "")), "stability": lst(brief.get("stability")),
                      "must_get": lst(brief.get("must_get")), "cut_first": lst(brief.get("cut_first"))},
            "carry_over": {k: str(carry.get(k, "")) for k in ("last_frame", "positions", "props", "costume", "lighting")},
            "assumptions": lst(a.get("assumptions")),
            "last_line": events[-1]["text"] if events else None,
            "last_speaker": events[-1]["speaker"] if events else None,
        }

    def submit(self, args: dict) -> dict:
        sub = self._normalise(args)
        report = self.check(sub["prompt"])
        self.attempts += 1
        sub["warnings"], sub["errors"], sub["timing"] = report["warnings"], report["errors"], report["timing"]
        if self.best is None or len(report["errors"]) < len(self.best["errors"]):
            self.best = sub
        left = self.max_attempts - self.attempts
        if not report["errors"]:
            sub["status"] = "ok"
            self.accepted = sub
        elif left <= 0:
            sub["status"] = "needs-review"
            self.accepted = self.best
            self.accepted["status"] = "needs-review"
        self.log.append({"attempt": self.attempts, "errors": len(report["errors"]), "warnings": len(report["warnings"])})
        return {"accepted": self.accepted is not None, "status": (self.accepted or {}).get("status", "rejected"),
                "errors": report["errors"], "warnings": report["warnings"], "timing": report["timing"], "attempts_left": max(0, left)}


def segment_tools(job: SegmentJob, console: Console, budget: AskBudget) -> list[Tool]:
    def check(args: dict) -> str:
        r = job.check(str(args["prompt"]))
        return json.dumps({"errors": r["errors"], "warnings": r["warnings"], "timing": r["timing"]}, ensure_ascii=False)

    def submit(args: dict) -> str:
        if args.get("segment_id") not in (None, job.segment["id"]):
            return json.dumps({"accepted": False, "errors": ["segment_id must be %s" % job.segment["id"]]})
        return json.dumps(job.submit(args), ensure_ascii=False)

    shot = {"type": "object", "properties": {"n": {"type": "integer"}, "scale": {"type": "string"}, "angle": {"type": "string"},
                                              "camera": {"type": "string"}, "seconds": {"type": "number"}, "function": {"type": "string"},
                                              "dialogue": {"type": ["string", "null"]}}}
    return [
        lookup_tool(),
        Tool("check_prompt", "Check a draft prompt without saving it. Returns errors (must fix), warnings and the timing estimate.",
             {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}, check),
        Tool("submit_segment_prompt", "Submit the finished prompt for this clip. It is saved only if it has no errors. "
             "Returns the errors to fix if it is rejected.",
             {"type": "object", "properties": {
                 "segment_id": {"type": "string"},
                 "prompt": {"type": "string", "description": "The paste-ready prompt text, nothing else."},
                 "shots": {"type": "array", "items": shot},
                 "brief": {"type": "object", "properties": {
                     "purpose": {"type": "string"}, "subject": {"type": "string"}, "subject_action": {"type": "string"},
                     "camera": {"type": "string"}, "environment": {"type": "string"}, "lighting": {"type": "string"},
                     "visual_direction": {"type": "string"}, "stability": {"type": "array", "items": {"type": "string"}},
                     "must_get": {"type": "array", "items": {"type": "string"}}, "cut_first": {"type": "array", "items": {"type": "string"}}}},
                 "carry_over": {"type": "object", "properties": {k: {"type": "string"} for k in ("last_frame", "positions", "props", "costume", "lighting")}},
                 "assumptions": {"type": "array", "items": {"type": "string"}}},
              "required": ["segment_id", "prompt", "shots", "brief", "carry_over"]}, submit),
        ask_user_tool(console, budget),
    ]


# ---------------------------------------------------------------------------
# the story analysis
# ---------------------------------------------------------------------------
@dataclass
class AnalysisJob:
    scene_numbers: list
    analysis: dict | None = None

    def submit(self, a: dict) -> dict:
        problems = []
        if not str(a.get("logline", "")).strip():
            problems.append("logline is empty")
        spine = a.get("spine")
        if not isinstance(spine, list) or not spine:
            problems.append("spine must list the acts")
        notes = a.get("scenes")
        if not isinstance(notes, list):
            problems.append("scenes must be a list with one note per scene")
        else:
            have = {int(n.get("scene", -1)) for n in notes if str(n.get("scene", "")).lstrip("-").isdigit()}
            missing = [n for n in self.scene_numbers if n not in have]
            if missing:
                problems.append("missing notes for scene(s): %s" % missing)
            for n in notes:
                if n.get("scene_type") and n["scene_type"] not in SCENE_TYPES:
                    problems.append("scene %s: scene_type %r is not one of %s" % (n.get("scene"), n["scene_type"], SCENE_TYPES))
        if problems:
            return {"accepted": False, "problems": problems}
        for n in a["scenes"]:  # a model may send scene numbers as strings
            n["scene"] = int(n["scene"])
        for act in a["spine"]:
            act["scenes"] = [int(x) for x in act.get("scenes", []) if str(x).lstrip("-").isdigit()]
        for key in ("characters", "locations", "color_script", "risks"):
            a[key] = [x for x in a.get(key, []) if isinstance(x, dict)]
        self.analysis = a
        return {"accepted": True}


def analysis_tools(job: AnalysisJob, console: Console, budget: AskBudget) -> list[Tool]:
    entry = {"type": "object"}
    schema = {"type": "object", "properties": {
        "logline": {"type": "string"}, "tone": {"type": "string"},
        "spine": {"type": "array", "items": {"type": "object", "properties": {
            "act": {"type": "string"}, "scenes": {"type": "array", "items": {"type": "integer"}}, "note": {"type": "string"}}}},
        "scenes": {"type": "array", "items": {"type": "object", "properties": {
            "scene": {"type": "integer"}, "why": {"type": "string"}, "scene_type": {"type": "string", "enum": SCENE_TYPES},
            "mood": {"type": "string"}, "camera_approach": {"type": "string"}, "status": {"type": "string", "enum": ["ready", "stub"]}}}},
        "characters": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "tag": {"type": "string"}, "look": {"type": "string"}, "voice": {"type": "string"},
            "aliases": {"type": "array", "items": {"type": "string"}},
            "lead": {"type": "boolean", "description": "true for a lead of the series"},
            "extra": {"type": "boolean", "description": "true for a minor character who gets no sheet and is described in full in each scene"},
            "source": {"type": "string", "enum": ["script", "assumed"]}}}},
        "locations": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "tag": {"type": "string"}}}},
        "style_lock": {"type": "string"},
        "color_script": {"type": "array", "items": {"type": "object", "properties": {
            "beat": {"type": "string"}, "emotion": {"type": "string"}, "dominant": {"type": "string"}, "accent": {"type": "string"},
            "contrast": {"type": "string"}, "saturation": {"type": "string"}, "hex": {"type": "array", "items": {"type": "string"}}}}},
        "motif": {"type": "string"},
        "risks": {"type": "array", "items": {"type": "object", "properties": {
            "item": {"type": "string"}, "why": {"type": "string"}, "alternative": {"type": "string"}}}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "assumptions": {"type": "array", "items": {"type": "string"}}},
        "required": ["logline", "spine", "scenes", "characters", "locations"]}
    return [
        Tool("submit_story_analysis", "Submit the episode analysis once. Returns problems to fix if it is incomplete.", schema,
             lambda a: json.dumps(job.submit(a), ensure_ascii=False)),
        ask_user_tool(console, budget),
    ]
