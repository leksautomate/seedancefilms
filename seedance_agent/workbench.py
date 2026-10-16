"""The studio's tools for a host agent.

When the studio runs inside an AI coding assistant (Claude Code, Gemini CLI, Antigravity, Cursor, VS Code, Codex ...), the
assistant's own model is the writer. This module is everything else: the gated tools it calls. They split the script, keep
the movie bible, check every sheet and prompt, and file the results under output/<Movie>/<Episode>/<Scene>/.

The tools keep no memory in the process. Everything lives in the episode folder (episode.json), so a tool call can come from
the MCP server, from `studio.py call`, or from a restarted session, and gives the same answer.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

from . import intake, prompts, script_doc, sheets
from .console import Console
from .intake import NeedInput
from .library import EpisodeFolder, Library
from .pipeline import (Options, _segment_view, _prev_info, apply_sheets_to_bible, attach_doc, merge_bible, run_episode, save_episode_files,
                       save_segment_files, save_sheet_files, scenes_for_location, scenes_for_names, seed_from_doc, speech_for)
from . import offline
from .tools import AnalysisJob, SegmentJob, camera_lookup, SCENE_TYPES
from .util import now_iso, read_json, sha

DERIVED = {"plan.html", "README.md", "prompts-all.md", "review-checklist.md", "characters-and-locations.md"}
GUIDES = {"workflow": "workflow.md", "story_analysis": "analyst.md", "sheets": "sheet_writer.md", "prompt_writing": "writer.md", "revising": "revise.md"}
HOST_NOTE = ("\n\n---\nThis guide was written for a program that gives the model a tool called `ask_user`. In this session there is no such tool: "
             "when the guide says to ask, ask the person directly in the chat, in one short message, and wait for the answer.\n")


class ToolError(Exception):
    """A problem the calling agent can fix. It becomes {"ok": false, "error": ...}."""


class _Folder(EpisodeFolder):
    """Regenerated overview files are rewritten in place, so a long session does not fill _history with drafts of them."""

    def write(self, relpath: str, text: str) -> Path:
        if relpath in DERIVED:
            target = self.path / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            self._written.add(target)
            return target
        return super().write(relpath, text)


class Workbench:
    def __init__(self, output: str | Path = "output"):
        self.output = str(output)
        self.lib = Library(self.output)

    # ------------------------------------------------------------------ helpers
    def _locate(self, movie: str, episode) -> tuple:
        found = self.lib.find_movie(str(movie or ""))
        if not found:
            raise ToolError("No movie called %r. Existing movies: %s. Start the episode with start_episode first." % (movie, ", ".join(self.lib.movies()) or "none"))
        mv = self.lib.open_movie(found)
        try:
            number = int(episode)
        except (TypeError, ValueError):
            raise ToolError("episode must be the episode number, for example 2.")
        epdir = mv.find_episode(number)
        state = read_json(epdir / "episode.json") if epdir else None
        if not state:
            raise ToolError("Episode %s of %s was not started. Existing episodes: %s." % (episode, found, ", ".join(str(n) for n, _, _ in mv.episode_folders()) or "none"))
        return mv, epdir, state, _Folder(epdir)

    def _doc(self, epdir: Path):
        f = epdir / "script.txt"
        return script_doc.parse(f.read_text(encoding="utf-8")) if f.exists() else None

    def _prepare(self, mv, epdir: Path, state: dict) -> None:
        """Bring the movie bible up to date from the analysis and the script. Existing entries win, so this can run any time."""
        segs = state["segments"]
        merge_bible(mv, state.get("analysis"), segs)
        doc = self._doc(epdir)
        if doc:
            seed_from_doc(mv, doc, segs)
        for s in segs:
            s["tags"] = [offline.tag_for(n, mv.bible) for n in s.get("characters", [])] + [offline.location_tag(s, mv.bible)[1]]
        state["settings"] = dict(mv.settings)
        mv.save()

    def _save(self, mv, folder: EpisodeFolder, state: dict) -> None:
        state["updated"] = now_iso()
        mv.save()
        save_episode_files(folder, state, False)

    @staticmethod
    def _core_names(state: dict, exclude_tag: str = "") -> list[dict]:
        names = [{"name": c["name"]} for c in (state.get("sheets") or {}).get("characters", []) if c.get("tag") != exclude_tag]
        names += [{"name": c["name"]} for c in (state.get("analysis") or {}).get("characters", []) if not c.get("extra") and c.get("name")]
        return names

    # ------------------------------------------------------------------ tools
    def list_movies(self) -> dict:
        out = []
        for m in self.lib.movies():
            mv = self.lib.open_movie(m)
            out.append({"movie": m, "episodes": [{"episode": n, "title": t} for n, t, _ in mv.episode_folders()],
                        "visual_style": mv.settings.get("visual_style"), "language_lock": bool(mv.settings.get("language_lock"))})
        return {"ok": True, "output_folder": self.output, "movies": out}

    def start_episode(self, script: str, movie: str | None = None, episode: int | None = None, title: str | None = None,
                      new_episode: bool = False, confirm_new_movie: bool = False, visual_style: str | None = None,
                      language_lock: bool | None = None, wps: float | None = None, clip: float | None = None, chain: float | None = None,
                      tone: str | None = None, fresh: bool = False) -> dict:
        text = script or ""
        if not text.strip():
            raise ToolError("The script is empty. Pass the whole script exactly as pasted.")
        doc = script_doc.parse(text)
        quiet = Console(interactive=False, out=io.StringIO())
        wanted = (movie or (doc.movie if doc else None) or intake.parse_header(text).movie or "").strip()
        if wanted and not self.lib.find_movie(wanted):
            close = self.lib.suggest(wanted)
            if close and not confirm_new_movie:
                return {"ok": False, "needs": "confirm_movie", "typed": wanted, "did_you_mean": close, "existing_movies": self.lib.movies(),
                        "ask": 'There is no movie called "%s". Did you mean "%s"? If it is really a new movie, call again with confirm_new_movie true.' % (wanted, close[0])}
        try:
            episode = int(episode) if episode not in (None, "") else None
        except (TypeError, ValueError):
            raise ToolError("episode must be a number.")
        episode = episode or (doc.episode_number if doc else None) or (None if new_episode else self._same_script(wanted, text))
        try:
            resolved = intake.resolve(text, self.lib, quiet, movie=wanted or None, episode=episode,
                                      title=title or (doc.episode_title if doc else None), new_episode=new_episode)
        except NeedInput:
            return {"ok": False, "needs": "movie", "existing_movies": self.lib.movies(),
                    "ask": "Which movie does this episode belong to? Every episode is filed under its movie. Give the name; do not guess it."}
        epdir = self.lib.open_movie(resolved.movie).find_episode(resolved.number)
        prior = read_json(epdir / "episode.json") if epdir else None
        same = bool(prior and prior.get("script_sha") == resolved.script_sha and not fresh)
        if same:
            mv = self.lib.open_movie(resolved.movie)
            for k, v in (("visual_style", visual_style), ("language_lock", language_lock), ("wps", wps), ("tone", tone)):
                if v is not None and v != "":
                    mv.settings[k] = v
            mv.save()
            prior["settings"] = dict(mv.settings)
            self._save(mv, _Folder(epdir), prior)
            return self._order(mv, epdir, prior, resumed=True)
        opts = Options(output=self.output, movie=resolved.movie, episode=resolved.number, title=resolved.title, plan_only=True, fresh=True,
                       visual_style=visual_style, language_lock=language_lock, wps=wps, clip=clip, chain=chain, tone=tone)
        try:
            result = run_episode(text, opts, quiet, None)
        except ValueError as e:
            raise ToolError(str(e))
        mv, epdir, state, folder = self._locate(resolved.movie, resolved.number)
        state.update({"source": "host agent", "provider": "host agent", "model": "the host agent's own model", "offline": False})
        self._prepare(mv, epdir, state)
        self._save(mv, folder, state)
        order = self._order(mv, epdir, state, resumed=False)
        order["new_movie"] = resolved.is_new_movie
        return order

    def _same_script(self, movie_name: str, text: str) -> int | None:
        """The episode number already holding exactly this script, so asking again resumes it instead of filing a copy."""
        found = self.lib.find_movie(movie_name) if movie_name else None
        if not found :
            return None
        for n, _, d in self.lib.open_movie(found).episode_folders():
            st = read_json(d / "episode.json")
            if st and st.get("script_sha") == sha(text):
                return n
        return None

    def _order(self, mv, epdir: Path, state: dict, resumed: bool) -> dict:
        self._prepare(mv, epdir, state)
        segs = state["segments"]
        ask = []
        if not mv.settings.get("visual_style"):
            ask.append({"need": "visual_style", "question": "What visual style should the characters, locations and scenes use?",
                        "examples": sheets.STYLE_EXAMPLES + ["Other (describe it)"],
                        "then": "Call start_episode again with the same script and visual_style."})
        speakers: dict = {}
        for s in segs:
            for e in s.get("events", []):
                if e.get("kind") == "dialogue" and e.get("speaker"):
                    speakers.setdefault(e["speaker"], set()).add(s["scene"])
        doc = state.get("script_doc") or {}
        return {"ok": True, "resumed": resumed, "movie": mv.name, "episode": state["number"], "title": state.get("title", ""), "path": str(epdir),
                "ask_the_person": ask, "settings": {k: v for k, v in mv.settings.items() if v not in (None, "")},
                "script": "production layout (scenes, planned seconds, character and location lists were read)" if doc else "plain script",
                "script_notes": {k: doc.get(k) for k in ("arc", "runtime_s", "setting", "opening", "end_card", "notes") if doc.get(k)},
                "script_lists": {"characters": doc.get("characters", []), "locations": doc.get("locations", [])} if doc else {},
                "speakers_and_their_scenes": {k: sorted(v) for k, v in sorted(speakers.items())},
                "clips": [dict(_segment_view(s, mv.bible), status=s.get("status", "pending")) for s in segs],
                "scene_numbers": sorted({s["scene"] for s in segs}),
                "bible": mv.bible, "progress": self._progress(state),
                "next": self._next(state, mv)}

    @staticmethod
    def _progress(state: dict) -> dict:
        segs = state["segments"]
        sh = state.get("sheets") or {}
        return {"analysis": bool(state.get("analysis")), "clips": len(segs), "clips_ok": sum(1 for s in segs if s.get("status") == "ok"),
                "clips_needs_review": [s["id"] for s in segs if s.get("status") == "needs-review"],
                "clips_pending": [s["id"] for s in segs if s.get("status", "pending") == "pending"],
                "character_sheets": [c["tag"] for c in sh.get("characters", [])], "location_sheets": [c["tag"] for c in sh.get("locations", [])],
                "extras": [x.get("name") for x in sh.get("extras", [])]}

    @staticmethod
    def _next(state: dict, mv) -> str:
        if not mv.settings.get("visual_style"):
            return "Ask the person for the visual style, then call start_episode again with it."
        if not state.get("analysis"):
            return "Read get_guide story_analysis, then call submit_story_analysis."
        if not (state.get("sheets") or {}).get("characters"):
            return "Show the person the character and location lists, then build the sheets with submit_sheet (read get_guide sheets first)."
        pending = [s["id"] for s in state["segments"] if s.get("status", "pending") == "pending"]
        if pending:
            return "Write the clips in order with check_prompt and submit_segment_prompt. Pending: %s." % ", ".join(pending)
        return "Call finish_episode and report to the person."

    def get_guide(self, name: str, movie: str | None = None, episode=None) -> dict:
        if name not in GUIDES:
            raise ToolError("Unknown guide %r. Guides: %s." % (name, ", ".join(GUIDES)))
        if name == "prompt_writing" and movie:
            mv, epdir, state, _ = self._locate(movie, episode)
            self._prepare(mv, epdir, state)
            text = prompts.writer_system({"name": mv.name, "settings": mv.settings, "bible": mv.bible})
        else:
            text = prompts.load(GUIDES[name])
        return {"ok": True, "guide": name, "text": text + (HOST_NOTE if name != "workflow" else "")}

    def lookup_camera_recipe(self, scene_type: str, mood: str = "") -> dict:
        return {"ok": True, "scene_types": SCENE_TYPES, "recipe": camera_lookup(scene_type, mood)}

    def submit_story_analysis(self, movie: str, episode, analysis: dict) -> dict:
        mv, epdir, state, folder = self._locate(movie, episode)
        job = AnalysisJob(sorted({s["scene"] for s in state["segments"]}))
        verdict = job.submit(analysis or {})
        if not verdict["accepted"]:
            return {"ok": False, "saved": False, "problems": verdict["problems"]}
        state["analysis"] = job.analysis
        if analysis.get("style_lock") and not mv.settings.get("style_lock"):
            mv.settings["style_lock"] = analysis["style_lock"]
        self._prepare(mv, epdir, state)
        self._save(mv, folder, state)
        return {"ok": True, "saved": True, "next": self._next(state, mv)}

    def submit_sheet(self, movie: str, episode, kind: str, entry: dict, save_anyway: bool = False) -> dict:
        mv, epdir, state, folder = self._locate(movie, episode)
        style = mv.settings.get("visual_style")
        if not style:
            return {"ok": False, "needs": "visual_style", "ask": "Ask the person for the visual style, then call start_episode again with it."}
        if kind not in ("character", "location"):
            raise ToolError("kind must be 'character' or 'location'.")
        segs = state["segments"]
        built = state.setdefault("sheets", {"style": style, "characters": [], "locations": [], "extras": []})
        built["style"] = style
        e = dict(entry or {})
        if kind == "character":
            speakers = [str(x).upper() for x in (e.get("speakers") or [e.get("name", "")]) if x]
            scenes = scenes_for_names(speakers, segs)
            recurring = len(scenes) > 1 or bool(e.get("lead"))
            job = sheets.SheetJob("character", style, others=self._core_names(state, e.get("tag", "")), speech_lines=speech_for(speakers, segs),
                                  recurring=recurring, max_attempts=1)
        else:
            scenes = scenes_for_location(e.get("match") or e.get("name", ""), segs)
            recurring = False
            job = sheets.SheetJob("location", style, characters=self._core_names(state), max_attempts=1)
        res = job.submit(e)
        rec = job.accepted
        if res["errors"] and not save_anyway:
            out = {"ok": False, "saved": False, "errors": res["errors"], "warnings": res["warnings"], "appears_in_scenes": scenes}
            if kind == "character":
                out["needs_voice_design_prompt"] = recurring
            return out
        ent = rec["entry"]
        ent["scenes"] = scenes
        if kind == "character":
            ent["speakers"] = speakers
        record = {"name": ent.get("name"), "tag": ent.get("tag"), "status": rec["status"], "errors": rec["errors"], "warnings": rec["warnings"],
                  "scenes": scenes, "entry": ent, "prompt": rec["prompt"]}
        if kind == "character":
            record["recurring"] = recurring
        bucket = built["characters" if kind == "character" else "locations"]
        bucket[:] = [r for r in bucket if r.get("tag") != record["tag"]] + [record]
        apply_sheets_to_bible(mv, built, segs)
        save_sheet_files(folder, built)
        self._prepare(mv, epdir, state)
        self._save(mv, folder, state)
        sub = "characters" if kind == "character" else "locations"
        return {"ok": True, "saved": True, "status": rec["status"], "file": "%s/%s.md" % (sub, record["tag"]), "warnings": rec["warnings"], "errors": rec["errors"],
                "voice_design_prompt_included": bool(ent.get("voice")), "next": self._next(state, mv)}

    def set_extras(self, movie: str, episode, extras: list) -> dict:
        mv, epdir, state, folder = self._locate(movie, episode)
        style = mv.settings.get("visual_style")
        if not style:
            return {"ok": False, "needs": "visual_style", "ask": "Ask the person for the visual style first."}
        clean = []
        for x in extras or []:
            if not isinstance(x, dict) or not str(x.get("name", "")).strip():
                raise ToolError("Each extra needs a name and a full description in 'look'.")
            if not str(x.get("look", "")).strip():
                raise ToolError("Extra %s needs a full description in 'look' (age, build, face, hair, clothes with colors). It is repeated in every scene prompt." % x["name"])
            clean.append({"name": str(x["name"]).strip(), "look": str(x["look"]).strip(), "voice": str(x.get("voice", "")).strip()})
        built = state.setdefault("sheets", {"style": style, "characters": [], "locations": [], "extras": []})
        built["extras"] = clean
        apply_sheets_to_bible(mv, built, state["segments"])
        save_sheet_files(folder, built)
        self._prepare(mv, epdir, state)
        self._save(mv, folder, state)
        return {"ok": True, "saved": True, "extras": [x["name"] for x in clean],
                "note": "Each scene prompt describes them in full inside the Characters line and in short at their first mention in every shot."}

    def _clip(self, state: dict, clip_id: str) -> tuple:
        segs = state["segments"]
        idx = next((i for i, s in enumerate(segs) if s["id"].lower() == str(clip_id).lower()), None)
        if idx is None:
            raise ToolError("No clip %r. Clips: %s" % (clip_id, ", ".join(s["id"] for s in segs)))
        seg = segs[idx]
        prev = segs[idx - 1] if idx > 0 and seg["mode"] in ("extend", "new-chain") else None
        return idx, seg, prev

    def check_prompt(self, movie: str, episode, segment_id: str, prompt: str) -> dict:
        mv, epdir, state, _ = self._locate(movie, episode)
        self._prepare(mv, epdir, state)
        idx, seg, prev = self._clip(state, segment_id)
        info = _prev_info(prev)
        if prev is not None and info is None:
            return {"ok": False, "error": "Clip %s continues %s, which has no saved prompt yet. Write and submit %s first." % (seg["id"], prev["id"], prev["id"])}
        job = SegmentJob(segment=seg, bible=mv.bible, settings=mv.settings, style="full", prev=info, max_attempts=1)
        r = job.check(str(prompt))
        return {"ok": True, "clip": seg["id"], "errors": r["errors"], "warnings": r["warnings"], "timing": r["timing"], "passes": not r["errors"]}

    def submit_segment_prompt(self, movie: str, episode, segment_id: str, prompt: str, shots: list | None = None, brief: dict | None = None,
                              carry_over: dict | None = None, assumptions: list | None = None, save_anyway: bool = False) -> dict:
        mv, epdir, state, folder = self._locate(movie, episode)
        self._prepare(mv, epdir, state)
        idx, seg, prev = self._clip(state, segment_id)
        info = _prev_info(prev)
        if prev is not None and info is None:
            return {"ok": False, "saved": False, "error": "Clip %s continues %s, which has no saved prompt yet. Submit %s first." % (seg["id"], prev["id"], prev["id"])}
        job = SegmentJob(segment=seg, bible=mv.bible, settings=mv.settings, style="full", prev=info, max_attempts=1)
        sub = {"prompt": prompt, "shots": shots or [], "brief": brief or {}, "carry_over": carry_over or {}, "assumptions": assumptions or []}
        report = job.check(str(prompt))
        if report["errors"] and not save_anyway:
            return {"ok": False, "saved": False, "errors": report["errors"], "warnings": report["warnings"], "timing": report["timing"],
                    "hint": "Fix exactly these errors and submit again. After three tries you may pass save_anyway true."}
        job.submit(sub)
        res = job.accepted
        seg.update({k: res[k] for k in ("prompt", "shots", "brief", "carry_over", "assumptions", "warnings", "errors", "timing", "status", "last_line", "last_speaker")})
        seg["attempts"] = seg.get("attempts", 0) + 1
        notes = {n.get("scene"): n for n in (state.get("analysis") or {}).get("scenes", [])}
        save_segment_files(folder, seg, notes.get(seg["scene"]), mv, False)
        later = [s["id"] for s in state["segments"][idx + 1:idx + 2] if s["mode"] in ("extend", "new-chain") and s.get("prompt")]
        self._save(mv, folder, state)
        return {"ok": True, "saved": True, "status": seg["status"], "warnings": seg["warnings"], "errors": seg["errors"], "timing": seg["timing"],
                "file": "%s/%s" % render_names(seg), "check_next": later, "next": self._next(state, mv)}

    def finish_episode(self, movie: str, episode) -> dict:
        mv, epdir, state, folder = self._locate(movie, episode)
        self._prepare(mv, epdir, state)
        notes = {n.get("scene"): n for n in (state.get("analysis") or {}).get("scenes", [])}
        for seg in state["segments"]:
            save_segment_files(folder, seg, notes.get(seg["scene"]), mv, False)
        self._save(mv, folder, state)
        p = self._progress(state)
        sh = state.get("sheets") or {}
        open_sheets = [c["tag"] for c in sh.get("characters", []) + sh.get("locations", []) if c.get("status") != "ok"]
        missing = [s["id"] for s in state["segments"] if not s.get("prompt")]
        proposed = sorted({a for s in state["segments"] for a in s.get("assumptions", []) if a})
        files = sorted(str(x.relative_to(epdir)) for x in epdir.rglob("*") if x.is_file() and "_history" not in x.parts and x.suffix in (".txt", ".md", ".html"))
        return {"ok": not missing, "path": str(epdir), "clips": p["clips"], "clips_ok": p["clips_ok"], "clips_needs_review": p["clips_needs_review"],
                "clips_without_a_prompt": missing, "sheets_needing_review": open_sheets,
                "estimated_seconds": round(sum(s.get("estimated_s", 0) for s in state["segments"]), 1),
                "assumptions": proposed, "unknowns": (state.get("analysis") or {}).get("unknowns", []),
                "files": files,
                "tell_the_person": "Where it is saved, how many clips are ready and which need review, what was assumed (marked proposed), "
                                   "and the next step: make the reference images from characters/ and locations/, save them in images/, "
                                   "then paste each scene prompt into Seedance 2.5."}

    def episode_status(self, movie: str, episode) -> dict:
        mv, epdir, state, _ = self._locate(movie, episode)
        return {"ok": True, "path": str(epdir), "progress": self._progress(state), "next": self._next(state, mv),
                "clips": [{"id": s["id"], "scene": s["scene"], "mode": s["mode"], "status": s.get("status", "pending"), "errors": s.get("errors", [])} for s in state["segments"]]}

    # ------------------------------------------------------------------ dispatch
    def call(self, name: str, args: dict | None = None) -> dict:
        fn = TOOLS.get(name)
        if fn is None:
            return {"ok": False, "error": "Unknown tool %r. Tools: %s" % (name, ", ".join(TOOLS))}
        try:
            return getattr(self, name)(**(args or {}))
        except ToolError as e:
            return {"ok": False, "error": str(e)}
        except TypeError as e:
            return {"ok": False, "error": "Wrong arguments for %s: %s" % (name, e)}
        except ValueError as e:
            return {"ok": False, "error": str(e)}


def render_names(seg: dict) -> tuple:
    from . import render
    sf, pfile, _ = render.seg_files(seg)
    return sf, pfile


S = {"type": "string"}
I = {"type": ["integer", "string"], "description": "The episode number, for example 2."}
B = {"type": "boolean"}
OBJ = {"type": "object"}
TOOLS = {
    "list_movies": ("The movies and episodes already filed in the output folder, with each movie's visual style.", {"type": "object", "properties": {}}),
    "start_episode": (
        "Start an episode from a pasted script: splits it into clips, files the plan, and returns the work order (clips with their spoken lines, "
        "the movie bible, what to ask the person). Pass the whole script exactly as pasted. If the movie is unknown it answers needs=movie: ask the person, "
        "never guess. Calling it again with the same script resumes.",
        {"type": "object", "properties": {"script": S, "movie": S, "episode": I, "title": S, "new_episode": B, "confirm_new_movie": B,
                                          "visual_style": {"type": "string", "description": "For example '2D anime'. Kept for the movie."},
                                          "language_lock": {"type": "boolean", "description": "Add the English-language lock lines to every scene prompt."},
                                          "wps": {"type": "number", "description": "Spoken words per second; 2.5 for slow solemn drama, default 3.4"},
                                          "clip": {"type": "number"}, "chain": {"type": "number"}, "tone": S, "fresh": B}, "required": ["script"]}),
    "get_guide": ("Read a guide before the step it belongs to. Guides: workflow, story_analysis, sheets, prompt_writing (pass movie and episode to include the movie's tags and voices), revising.",
                  {"type": "object", "properties": {"name": {"type": "string", "enum": list(GUIDES)}, "movie": S, "episode": I}, "required": ["name"]}),
    "lookup_camera_recipe": ("The camera recipe and shot flow for a scene type.",
                             {"type": "object", "properties": {"scene_type": {"type": "string", "enum": SCENE_TYPES}, "mood": S}, "required": ["scene_type"]}),
    "submit_story_analysis": ("Submit the episode analysis once: logline, spine, a note for every scene, characters, locations, colour script, risks, unknowns. "
                              "Returns the problems to fix if it is incomplete.",
                              {"type": "object", "properties": {"movie": S, "episode": I, "analysis": OBJ}, "required": ["movie", "episode", "analysis"]}),
    "submit_sheet": ("Submit one character sheet or one location sheet (fields in the 'sheets' guide). The prompt is rendered from your fields and saved only if it "
                     "passes the checks. A character in more than one scene, or the lead, needs a 'voice' object (voice design prompt).",
                     {"type": "object", "properties": {"movie": S, "episode": I, "kind": {"type": "string", "enum": ["character", "location"]}, "entry": OBJ, "save_anyway": B},
                      "required": ["movie", "episode", "kind", "entry"]}),
    "set_extras": ("Characters who get no sheet (a dealer, guards): each needs a full description in 'look'. Scene prompts then describe them in full.",
                   {"type": "object", "properties": {"movie": S, "episode": I, "extras": {"type": "array", "items": {"type": "object", "properties": {
                       "name": S, "look": S, "voice": S}, "required": ["name", "look"]}}}, "required": ["movie", "episode", "extras"]}),
    "check_prompt": ("Test a draft prompt for one clip against all the checks. Nothing is saved. Returns errors (must fix), warnings and the timing estimate.",
                     {"type": "object", "properties": {"movie": S, "episode": I, "segment_id": S, "prompt": S}, "required": ["movie", "episode", "segment_id", "prompt"]}),
    "submit_segment_prompt": ("Submit the finished prompt for one clip. Saved only if it has no errors (or save_anyway is true, which files it as needs-review). "
                              "Spoken lines must be the script's, word for word.",
                              {"type": "object", "properties": {
                                  "movie": S, "episode": I, "segment_id": S, "prompt": {"type": "string", "description": "The paste-ready prompt text, nothing else."},
                                  "shots": {"type": "array", "items": OBJ}, "brief": OBJ, "carry_over": OBJ, "assumptions": {"type": "array", "items": S}, "save_anyway": B},
                               "required": ["movie", "episode", "segment_id", "prompt"]}),
    "finish_episode": ("Write the plan page, README, prompt list and review checklist, and report what is open. Call it when every clip has a prompt.",
                       {"type": "object", "properties": {"movie": S, "episode": I}, "required": ["movie", "episode"]}),
    "episode_status": ("Where an episode stands: analysis, sheets, each clip's status, and the next step.",
                       {"type": "object", "properties": {"movie": S, "episode": I}, "required": ["movie", "episode"]}),
}


START, END = "<!-- workflow:start (generated from seedance_agent/prompts/workflow.md; run `python3 studio.py sync-agents`) -->", "<!-- workflow:end -->"


def sync_agents_md(path: str | Path = "AGENTS.md", check: bool = False) -> bool:
    """Copy the workflow into AGENTS.md between the markers. With check=True only report whether the file is up to date."""
    f = Path(path)
    text = f.read_text(encoding="utf-8")
    a, b = text.index(START.split(" (")[0]), text.index(END)
    new = text[:a] + START + "\n\n" + prompts.load("workflow.md").strip() + "\n\n" + text[b:]
    if check:
        return new == text
    f.write_text(new, encoding="utf-8")
    return True
