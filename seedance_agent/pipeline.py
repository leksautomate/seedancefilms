"""The studio pipeline: script in, organised prompts out.

  paste a script
    -> intake        which movie, which episode (asks if the movie is not given)
    -> segmenter     scenes -> clips (up to 30 s each, extension and new chains beyond, short clips)   [code]
    -> analyst       spine, why each scene earns its place, bible, colour, risks         [model agent]
    -> writer        one agent loop per clip, every prompt gated by the linter           [model agent]
    -> library       output/<Movie>/<Episode>/<Scene>/ files, plan.html, README, review checklist

Progress is saved after every clip, so an interrupted run resumes where it stopped.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import intake, offline, planpage, prompts, render, script_doc, sheets
from . import skills_bridge as sb
from .agent import run_loop
from .console import Console
from .library import EpisodeFolder, Library, Movie
from .llm import LLM
from .tools import AnalysisJob, AskBudget, SegmentJob, analysis_tools, segment_tools
from .util import norm_key, now_iso, read_json, title_case, write_json


@dataclass
class Options:
    output: str = "output"
    movie: str | None = None
    episode: int | None = None
    title: str | None = None
    new_episode: bool = False
    offline: bool = False
    clip: float | None = None
    chain: float | None = None
    max_attempts: int = 4
    fresh: bool = False
    style: str = "full"
    tone: str | None = None
    wps: float | None = None          # spoken words per second (slower for solemn drama)
    plan_only: bool = False           # segment and file the plan, write no prompts
    prompts_file: str | None = None   # prompts (and an analysis) written elsewhere, filed through the same checks
    visual_style: str | None = None   # for the character and location sheets, for example "2D anime"
    sheets: str = "auto"              # auto: build the sheets, only: sheets and no scene prompts, skip: no sheets


# ---------------------------------------------------------------------------
# bible
# ---------------------------------------------------------------------------
def merge_bible(movie: Movie, analysis: dict | None, segments: list[dict]) -> None:
    """Add what the analysis found to the movie bible. Entries that already exist win."""
    chars = movie.bible.setdefault("characters", {})
    locs = movie.bible.setdefault("locations", {})
    for c in (analysis or {}).get("characters", []):
        name = str(c.get("name", "")).strip().upper()
        if not name:
            continue
        cur = chars.setdefault(name, {})
        for k in ("tag", "look", "voice"):
            if k == "tag" and cur.get("no_image"):
                continue   # an extra with no reference image is described in full, never tagged
            if not cur.get(k) and c.get(k):
                cur[k] = c[k]
        cur.setdefault("source", c.get("source", "script"))
        for alias in c.get("aliases") or []:   # the script's other names for the same person ("SULTAN ALI" for "ALI")
            a = chars.setdefault(str(alias).strip().upper(), {})
            for k in ("tag", "look", "voice"):
                if not a.get(k) and cur.get(k):
                    a[k] = cur[k]
            a.setdefault("alias_of", name)
    for l in (analysis or {}).get("locations", []):
        name = str(l.get("name", "")).strip()
        if not name:
            continue
        key = next((k for k in locs if norm_key(k) == norm_key(name)), name)
        cur = locs.setdefault(key, {})
        if not cur.get("tag") and l.get("tag"):
            cur["tag"] = l["tag"]
    for s in segments:  # everyone in the script gets at least a default tag
        for name in s.get("characters", []):
            cur = chars.setdefault(name, {"source": "assumed"})
            if not cur.get("no_image"):
                cur.setdefault("tag", "@ TAG %s" % name.upper())
        if s.get("location"):
            label = s.get("location_label") or title_case(s["location"])
            key = next((k for k in locs if norm_key(k) == norm_key(label) or norm_key(k) == norm_key(s["location"])), label)
            locs.setdefault(key, {}).setdefault("tag", script_doc.tag_for_place(label) if s.get("location_label") else "@ TAG %s" % s["location"].upper())
    style = (analysis or {}).get("style_lock")
    if style and not movie.settings.get("style_lock"):
        movie.settings["style_lock"] = style


def offline_analysis(segments: list[dict]) -> dict:
    scenes = []
    seen = set()
    for s in segments:
        if s["scene"] in seen:
            continue
        seen.add(s["scene"])
        scenes.append({"scene": s["scene"], "why": "Not analysed: run with a model to fill this in.", "scene_type": _scene_type(s),
                       "mood": s.get("mood_hint", "neutral"), "camera_approach": "Locked-off framing with hard cuts.", "status": "ready"})
    return {"logline": "", "tone": "", "spine": [{"act": "Episode", "scenes": sorted(seen), "note": "No act structure without a model."}],
            "scenes": scenes, "characters": [], "locations": [], "unknowns": ["Voices, looks and style were not analysed (offline)."], "assumptions": []}


def _scene_type(seg: dict) -> str:
    hint = seg.get("scene_type_hint") or "dialogue"
    return {"environment_establishing": "environment_establishing", "static_or_insert": "static_emotion", "action": "action",
            "revelation": "revelation", "suspense_horror": "suspense_horror", "farewell_ending": "farewell_ending",
            "character_entrance": "character_entrance", "montage_transition": "montage_transition"}.get(hint, "dialogue")


# ---------------------------------------------------------------------------
# context given to the model
# ---------------------------------------------------------------------------
def _segment_view(seg: dict, bible: dict) -> dict:
    chars = {n: {"tag": (bible["characters"].get(n) or {}).get("tag"), "voice": (bible["characters"].get(n) or {}).get("voice"),
                 "look": (bible["characters"].get(n) or {}).get("look"), "no_image": bool((bible["characters"].get(n) or {}).get("no_image"))}
             for n in seg.get("characters", [])}
    loc_name, loc_tag = offline.location_tag(seg, bible)
    return {"id": seg["id"], "scene": seg["scene"], "heading": seg.get("heading"), "mode": seg["mode"], "part": seg.get("part"),
            "parts": seg.get("parts"), "estimated_s": seg.get("estimated_s"), "request_s": seg.get("request_s"),
            "location": {"name": loc_name, "tag": loc_tag}, "characters": chars,
            "events": [{"kind": e["kind"], "speaker": e.get("speaker"), "how": e.get("how"), "text": e["text"], "seconds": e.get("seconds")} for e in seg.get("events", [])],
            "scene_title": seg.get("scene_title"), "planned_s": seg.get("planned_s"), "on_screen_per_script": seg.get("on_screen"),
            "edit_overlays_not_for_the_model_to_draw": seg.get("overlays"), "notes": seg.get("notes", [])}


def _prev_info(prev_seg: dict | None) -> dict | None:
    if not prev_seg or not prev_seg.get("prompt"):
        return None
    return {"id": prev_seg["id"], "last_line": prev_seg.get("last_line"), "last_speaker": prev_seg.get("last_speaker"),
            "carry_over": prev_seg.get("carry_over"), "prompt_tail": prev_seg["prompt"][-1400:]}


def _analysis_text(script: str, segments: list[dict], movie: Movie) -> str:
    plan = [{"id": s["id"], "scene": s["scene"], "heading": s.get("heading"), "mode": s["mode"], "estimated_s": s.get("estimated_s"),
             "dialogue_lines": s.get("dialogue_lines"), "scene_type_hint": s.get("scene_type_hint"), "mood_hint": s.get("mood_hint")} for s in segments]
    return ("Analyse this episode.\n\n## The script\n\n%s\n\n## The segment plan (computed from the script)\n\n```json\n%s\n```\n\n"
            "## The movie bible so far (existing entries win)\n\n```json\n%s\n```\n\n## Settings\n\n```json\n%s\n```\n" % (
                script, json.dumps(plan, indent=1), json.dumps(movie.bible, indent=1, ensure_ascii=False), json.dumps(movie.settings, indent=1)))


def attach_doc(segs: list[dict], doc: script_doc.Doc) -> None:
    """Copy what the production script says about each scene onto its clips."""
    by = {sc.number: sc for sc in doc.scenes}
    for s in segs:
        sc = by.get(s["scene"])
        if not sc:
            continue
        s["scene_title"], s["planned_s"], s["clip_block"] = sc.title, sc.planned_s, sc.clip
        s["on_screen"], s["overlays"] = sc.on_screen, sc.overlays
        s["location_label"] = script_doc.match_location(doc, sc.place) if sc.place else None


def doc_summary(doc: script_doc.Doc) -> dict:
    return {"movie": doc.movie, "arc": doc.arc, "runtime_s": doc.runtime_s, "setting": doc.setting, "opening": doc.opening,
            "end_card": doc.end_card, "notes": doc.notes, "blocks": doc.blocks,
            "characters": [{k: c[k] for k in ("name", "qualifier", "look", "voice")} for c in doc.characters],
            "locations": doc.locations}


def seed_from_doc(movie: Movie, doc: script_doc.Doc, segs: list[dict]) -> None:
    """Fill empty look and voice fields from the script's CORE CHARACTERS list. Existing entries win."""
    speakers = sorted({e["speaker"] for s in segs for e in s.get("events", []) if e.get("kind") == "dialogue" and e.get("speaker")})
    for name, found in script_doc.bible_seed(doc, speakers).items():
        cur = movie.bible["characters"].setdefault(name, {})
        for k in ("look", "voice"):
            if not cur.get(k) and found.get(k):
                cur[k] = found[k]
        cur.setdefault("source", "script")


def submit_external(seg: dict, movie: Movie, prev_seg: dict | None, sub: dict, opts: "Options") -> dict:
    """File a prompt written elsewhere. It goes through the same checks, once, with no retries."""
    job = SegmentJob(segment=seg, bible=movie.bible, settings=movie.settings, style=opts.style, prev=_prev_info(prev_seg), max_attempts=1)
    job.submit(sub)
    if job.accepted is None:
        job.accepted = job.best
        job.accepted["status"] = "needs-review"
    return {**job.accepted, "attempts": 1, "turns": 0}


# ---------------------------------------------------------------------------
# character and location sheets
# ---------------------------------------------------------------------------
def _norm(s: str) -> str:
    return norm_key(s)


def scenes_for_names(names: list[str], segs: list[dict]) -> list[int]:
    want = {n.upper() for n in names}
    out = set()
    for s in segs:
        present = set(s.get("characters", [])) | {e.get("speaker") for e in s.get("events", []) if e.get("speaker")}
        if want & present:
            out.add(s["scene"])
    return sorted(out)


def scenes_for_location(name: str, segs: list[dict]) -> list[int]:
    key = _norm(name)
    return sorted({s["scene"] for s in segs if s.get("location_label") and (key in _norm(s["location_label"]) or _norm(s["location_label"]) in key)})


def speech_for(names: list[str], segs: list[dict]) -> list[str]:
    want = {n.upper() for n in names}
    out = []
    for s in segs:
        for e in s.get("events", []):
            if e.get("kind") == "dialogue" and e.get("speaker") in want and e["text"] not in out:
                out.append(e["text"])
    return out


def build_sheets(text: str, doc, segs: list[dict], state: dict, movie: Movie, llm, external, console: Console, opts: "Options") -> dict | None:
    """Character and location continuity sheets (see sheets.py). Returns the saved state, or None when they were not built."""
    if opts.sheets == "skip":
        return None
    style = movie.settings.get("visual_style")
    if not style:
        if console.interactive:
            style = console.ask("What visual style should the character and location sheets use?", sheets.STYLE_EXAMPLES + ["Other (describe it)"])
            if style.startswith("Other"):
                style = console.ask("Describe the style.")
            movie.settings["visual_style"] = style
        else:
            console.say("No visual style is set, so the character and location sheets were skipped. Use --visual-style \"2D anime\" (or similar).")
            return None
    spec = (external or {}).get("sheets")
    if external is not None and not spec:
        return None
    if external is None and llm is None:
        console.say("Character and location sheets need a model (or --prompts). Skipped.")
        return None
    analysis = state["analysis"]
    if spec:
        char_in, loc_in, extras = spec.get("characters", []), spec.get("locations", []), spec.get("extras", [])
    else:
        char_in = [c for c in analysis.get("characters", []) if not c.get("extra")]
        loc_in = list(analysis.get("locations", []))
        extras = [c for c in analysis.get("characters", []) if c.get("extra")]
    all_chars = [{"name": c.get("name", "")} for c in char_in]
    out = {"style": style, "characters": [], "locations": [], "extras": extras}
    console.say("Building %d character sheets and %d location sheets in %s ..." % (len(char_in), len(loc_in), style))

    def run(kind: str, base: dict, job: "sheets.SheetJob") -> dict:
        if spec:
            job.submit(base)
        else:
            ctx = {"kind": kind, "visual_style": style, "entry": base, "needs_voice_design_prompt": job.recurring if kind == "character" else None,
                   "scenes_it_appears_in": base.get("scenes"), "its_own_script_lines": job.speech_lines, "other_core_characters": [c["name"] for c in all_chars]}
            user = "Fill the fields for this %s sheet.\n\n## The script\n\n%s\n\n## The entry\n\n```json\n%s\n```\n" % (kind, text, json.dumps(ctx, indent=1, ensure_ascii=False))
            run_loop(llm, prompts.load("sheet_writer.md"), user, sheets.sheet_tools(job, console, AskBudget(1)), done=lambda: job.accepted is not None,
                     max_turns=8, nudge="Call submit_sheet now.")
        if job.accepted is None:
            job.accepted = job.best or {"entry": base, "prompt": "", "errors": ["The model did not submit this sheet."], "warnings": []}
            job.accepted["status"] = "needs-review"
        return job.accepted

    for c in char_in:
        speakers = [x.upper() for x in (c.get("speakers") or [c.get("name", "")])]
        scenes = scenes_for_names(speakers, segs)
        lines = speech_for(speakers, segs)
        recurring = len(scenes) > 1 or bool(c.get("lead"))
        base = {**c, "scenes": scenes}
        job = sheets.SheetJob("character", style, others=[x for x in all_chars if x["name"] != c.get("name")], speech_lines=lines, recurring=recurring)
        res = run("character", base, job)
        e = res["entry"]
        e["scenes"], e["speakers"] = scenes, speakers
        out["characters"].append({"name": e.get("name"), "tag": e.get("tag"), "status": res["status"], "errors": res["errors"], "warnings": res["warnings"],
                                  "recurring": recurring, "scenes": scenes, "entry": e, "prompt": res["prompt"]})
        console.say("  %s %s: %s%s" % (e.get("tag"), "(voice design)" if e.get("voice") else "", res["status"], (", %d problems" % len(res["errors"])) if res["errors"] else ""))
    for l in loc_in:
        scenes = scenes_for_location(l.get("match") or l.get("name", ""), segs)
        job = sheets.SheetJob("location", style, characters=all_chars)
        res = run("location", {**l, "scenes": scenes}, job)
        e = res["entry"]
        e["scenes"] = scenes
        out["locations"].append({"name": e.get("name"), "tag": e.get("tag"), "status": res["status"], "errors": res["errors"], "warnings": res["warnings"],
                                 "scenes": scenes, "entry": e, "prompt": res["prompt"]})
        console.say("  %s: %s%s" % (e.get("tag"), res["status"], (", %d problems" % len(res["errors"])) if res["errors"] else ""))
    return out


def apply_sheets_to_bible(movie: Movie, built: dict, segs: list[dict]) -> None:
    """The sheet tags become the bible tags, so every scene prompt names the same images."""
    chars = movie.bible.setdefault("characters", {})
    locs = movie.bible.setdefault("locations", {})
    for c in built["characters"]:
        e = c["entry"]
        for sp in e.get("speakers") or [str(e.get("name", "")).upper()]:
            cur = chars.setdefault(sp, {})
            if not cur.get("tag") or cur["tag"].startswith("@ TAG "):
                cur["tag"] = e["tag"]
            for k, v in (("look", e.get("outfit_summary") or e.get("traits")), ("voice", e.get("video_voice") or e.get("speech_style"))):
                if v and not cur.get(k):
                    cur[k] = v
            cur.setdefault("source", "script")
            cur.pop("no_image", None)
    for x in built.get("extras", []):
        name = str(x.get("name", "")).upper()
        cur = chars.setdefault(name, {})
        cur["no_image"], cur["tag"] = True, ""
        if x.get("look"):
            cur["look"] = x["look"]
        if x.get("voice") and not cur.get("voice"):
            cur["voice"] = x["voice"]
    for l in built["locations"]:
        e = l["entry"]
        key = e.get("match") or e.get("name")
        label = next((s.get("location_label") for s in segs if s.get("location_label") and (_norm(key) in _norm(s["location_label"]) or _norm(s["location_label"]) in _norm(key))), None)
        k = next((k for k in locs if _norm(k) == _norm(label or key)), label or key)
        cur = locs.setdefault(k, {})
        if not cur.get("tag") or cur["tag"].startswith("@ TAG "):
            cur["tag"] = e["tag"]


def save_sheet_files(folder: EpisodeFolder, built: dict) -> None:
    style = built["style"]
    for c in built["characters"]:
        folder.write("characters/%s.md" % c["tag"], sheets.character_file(c["entry"], style))
    for l in built["locations"]:
        folder.write("locations/%s.md" % l["tag"], sheets.location_file(l["entry"], style))
    for d in ("images/characters", "images/locations"):
        (folder.path / d).mkdir(parents=True, exist_ok=True)
        (folder.path / d / ".gitkeep").touch()
    folder.write("characters-and-locations.md", sheets.lists_md([c["entry"] for c in built["characters"]], [l["entry"] for l in built["locations"]], style, built.get("extras")))


# ---------------------------------------------------------------------------
# one clip
# ---------------------------------------------------------------------------
def write_segment(seg: dict, movie: Movie, scene_note: dict | None, prev_seg: dict | None, next_seg: dict | None,
                  llm: LLM | None, console: Console, opts: Options, revision: str | None = None) -> dict:
    prev = _prev_info(prev_seg)
    job = SegmentJob(segment=seg, bible=movie.bible, settings=movie.settings, style=opts.style, prev=prev, max_attempts=opts.max_attempts)
    if llm is None:
        sub = offline.draft(seg, movie.bible, movie.settings, prev)
        job.submit(sub)
        for _ in range(opts.max_attempts):
            if job.accepted:
                break
            job.submit(sub)
        return {**job.accepted, "attempts": job.attempts, "turns": 0}

    first = {"segment": _segment_view(seg, movie.bible), "scene_note": scene_note, "previous_clip": prev,
             "next_clip_starts_with": (next_seg["events"][0]["text"] if next_seg and next_seg.get("events") else None),
             "style": opts.style, "aspect_ratio": movie.settings.get("aspect_ratio")}
    system = prompts.writer_system(movie.data)
    if revision:
        first["revision_request"] = revision
        first["current_prompt"] = seg.get("prompt")
        system += "\n\n# Revision\n\n" + prompts.revise_note()
    user = "Write the prompt for this clip.\n\n```json\n%s\n```" % json.dumps(first, indent=1, ensure_ascii=False)
    budget = AskBudget(1)
    res = run_loop(llm, system, user, segment_tools(job, console, budget), done=lambda: job.accepted is not None,
                   max_turns=6 + 2 * opts.max_attempts, nudge="You have not submitted an accepted prompt yet. Call submit_segment_prompt now.",
                   on_event=None)
    if job.accepted is None:
        if job.best is None:
            # the model never submitted a prompt: keep the episode moving with a labelled template draft
            sub = offline.draft(seg, movie.bible, movie.settings, prev)
            job.submit(sub)
            job.accepted = job.best
            job.accepted["status"] = "needs-review"
            job.accepted["errors"] = ["The model did not submit a prompt for this clip. This is an offline template draft: rewrite it or run again."]
        else:
            job.accepted = job.best
            job.accepted["status"] = "needs-review"
    return {**job.accepted, "attempts": job.attempts, "turns": res.turns}


# ---------------------------------------------------------------------------
# saving
# ---------------------------------------------------------------------------
def save_segment_files(folder: EpisodeFolder, seg: dict, scene_note: dict | None, movie: Movie, offline_mode: bool) -> None:
    sf, pfile, bfile = render.seg_files(seg)
    if seg.get("prompt"):
        folder.write("%s/%s" % (sf, pfile), seg["prompt"])
    folder.write("%s/%s" % (sf, bfile), render.brief_md(seg, scene_note, movie.settings, offline_mode))


def save_episode_files(folder: EpisodeFolder, state: dict, offline_mode: bool) -> None:
    write_json(folder.path / "episode.json", state)
    folder.write("plan.html", planpage.render(state, offline_mode))
    folder.write("prompts-all.md", render.prompts_all_md(state))
    folder.write("README.md", render.readme_md(state, offline_mode))
    folder.write("review-checklist.md", render.review_md(state))


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------
def run_episode(text: str, opts: Options, console: Console, llm: LLM | None) -> dict:
    if not text.strip():
        raise ValueError("The script is empty.")
    lib = Library(opts.output)
    doc = script_doc.parse(text)   # an annotated production script, or None for a plain script
    resolved = intake.resolve(text, lib, console, movie=opts.movie or (doc.movie if doc else None),
                              episode=opts.episode or (doc.episode_number if doc else None),
                              title=opts.title or (doc.episode_title if doc else None), new_episode=opts.new_episode)
    external = json.loads(Path(opts.prompts_file).read_text(encoding="utf-8")) if opts.prompts_file else None
    offline_mode = llm is None and external is None and not opts.plan_only
    movie = lib.open_movie(resolved.movie)
    if opts.clip:
        movie.settings["clip_seconds"] = opts.clip
    if opts.chain:
        movie.settings["chain_seconds"] = opts.chain
    if opts.tone:
        movie.settings["tone"] = opts.tone
    if opts.wps:
        movie.settings["wps"] = opts.wps
    for k, v in ((external or {}).get("settings") or {}).items():
        movie.settings[k] = v
    epdir = movie.episode_dir(resolved.number, resolved.title)
    folder = EpisodeFolder(epdir)
    prior = read_json(epdir / "episode.json")
    resume = bool(prior and prior.get("script_sha") == resolved.script_sha and not opts.fresh and prior.get("offline") == offline_mode)
    console.say("")
    console.say("%s → Episode %02d%s%s" % (movie.name, resolved.number, (" — " + resolved.title) if resolved.title else "",
                                                " (new movie)" if resolved.is_new_movie else ""))
    console.say("Resuming the saved run." if resume else ("Replacing the earlier version of this episode (it is kept in _history)." if prior else "Starting a new episode."))

    segs = prior["segments"] if resume else sb.segment(doc.normalized if doc else text, clip=movie.settings["clip_seconds"],
                                                       chain=movie.settings["chain_seconds"], wps=movie.settings.get("wps"))
    if not segs:
        raise ValueError("No scenes were found in the script.")
    if doc and not resume:
        attach_doc(segs, doc)
        console.say("Read the production script: %d scenes, %d characters, %d locations, runtime plan %s." % (
            len(doc.scenes), len(doc.characters), len(doc.locations), ("%d:%02d" % divmod(doc.runtime_s, 60)) if doc.runtime_s else "n/a"))
    for s in segs:
        s.setdefault("status", "pending")
    scene_numbers = sorted({s["scene"] for s in segs})
    console.say("%d scenes → %d clips, about %.0f seconds." % (len(scene_numbers), len(segs), sum(s.get("estimated_s", 0) for s in segs)))

    state = {"movie": movie.name, "number": resolved.number, "title": resolved.title, "script_sha": resolved.script_sha,
             "created": (prior or {}).get("created") or now_iso(), "updated": now_iso(), "offline": offline_mode,
             "source": "external" if external is not None else ("plan-only" if opts.plan_only else ("offline" if llm is None else "model")),
             "provider": "external" if external is not None else getattr(llm, "provider", "offline"),
             "model": "written outside the program" if external is not None else getattr(llm, "model", "template"), "settings": dict(movie.settings),
             "script_doc": (prior or {}).get("script_doc") if resume else (doc_summary(doc) if doc else None),
             "analysis": (prior or {}).get("analysis") if resume else None, "segments": segs}
    if not resume:
        folder.write("script.txt", text)
    save_episode_files(folder, state, offline_mode)
    movie.save()
    if opts.plan_only:
        console.say("Plan only: no prompts were written.")
        return {"movie": movie.name, "number": resolved.number, "title": resolved.title, "path": str(epdir), "segments": len(segs), "ok": 0,
                "needs_review": [], "usage": {}, "state": state}

    # ---- analysis ---------------------------------------------------------
    if state["analysis"] is None:
        if external is not None and external.get("analysis"):
            job = AnalysisJob(scene_numbers)
            verdict = job.submit(external["analysis"])
            if not verdict["accepted"]:
                raise ValueError("The supplied analysis is incomplete: %s" % "; ".join(verdict["problems"]))
            state["analysis"] = job.analysis
        elif llm is None:
            state["analysis"] = offline_analysis(segs)
        else:
            console.say("Reading the whole episode (spine, scene notes, characters, voices, colour, risks) ...")
            job = AnalysisJob(scene_numbers)
            run_loop(llm, prompts.analyst_system(), _analysis_text(text, segs, movie), analysis_tools(job, console, AskBudget(1)),
                     done=lambda: job.analysis is not None, max_turns=10, nudge="Call submit_story_analysis now.")
            if job.analysis is None:
                console.say("The analysis was not accepted. Continuing with a basic plan; scene notes will be empty.")
                state["analysis"] = offline_analysis(segs)
            else:
                state["analysis"] = job.analysis
    if opts.visual_style:
        movie.settings["visual_style"] = opts.visual_style
    built = build_sheets(text, doc, segs, state, movie, llm, external, console, opts)
    if built:
        state["sheets"] = built
        apply_sheets_to_bible(movie, built, segs)
        save_sheet_files(folder, built)
    merge_bible(movie, state["analysis"], segs)
    if doc:
        seed_from_doc(movie, doc, segs)
    movie.save()
    if opts.sheets == "only":
        state["updated"] = now_iso()
        save_episode_files(folder, state, offline_mode)
        return {"movie": movie.name, "number": resolved.number, "title": resolved.title, "path": str(epdir), "segments": len(segs), "ok": 0,
                "needs_review": [c["tag"] for c in (built or {}).get("characters", []) + (built or {}).get("locations", []) if c["status"] != "ok"],
                "usage": {}, "state": state}
    state["settings"] = dict(movie.settings)
    for s in segs:
        s["tags"] = [offline.tag_for(n, movie.bible) for n in s.get("characters", [])] + [offline.location_tag(s, movie.bible)[1]]
    save_episode_files(folder, state, offline_mode)
    notes = {n.get("scene"): n for n in state["analysis"].get("scenes", [])}

    # ---- the clips --------------------------------------------------------
    for i, seg in enumerate(segs):
        if seg.get("status") == "ok" and seg.get("prompt"):
            console.say("  %s already done." % seg["id"])
            continue
        console.say("  Writing %s (%s, %.1fs) ..." % (seg["id"], seg["mode"], seg.get("estimated_s", 0)))
        prev_seg = segs[i - 1] if i > 0 and seg["mode"] in ("extend", "new-chain") else None
        nxt = segs[i + 1] if i + 1 < len(segs) else None
        if external is not None:
            sub = (external.get("prompts") or {}).get(seg["id"])
            if sub is None:
                console.say("    no prompt supplied for %s; left pending." % seg["id"])
                continue
            result = submit_external(seg, movie, prev_seg, sub, opts)
        else:
            result = write_segment(seg, movie, notes.get(seg["scene"]), prev_seg, nxt, llm, console, opts)
        seg.update({k: result[k] for k in ("prompt", "shots", "brief", "carry_over", "assumptions", "warnings", "errors", "timing", "status",
                                           "last_line", "last_speaker", "attempts")})
        t = seg["timing"]
        console.say("    %s — %.1fs estimated, %d warnings%s" % (seg["status"], t["estimated_s"], len(seg["warnings"]),
                                                                    ", %d open problems" % len(seg["errors"]) if seg["errors"] else ""))
        state["updated"] = now_iso()
        save_segment_files(folder, seg, notes.get(seg["scene"]), movie, offline_mode)
        save_episode_files(folder, state, offline_mode)

    state["usage"] = {"calls": getattr(llm, "calls", 0), "input_tokens": getattr(llm, "input_tokens", 0), "output_tokens": getattr(llm, "output_tokens", 0)}
    state["updated"] = now_iso()
    for seg in segs:
        save_segment_files(folder, seg, notes.get(seg["scene"]), movie, offline_mode)
    save_episode_files(folder, state, offline_mode)
    return {"movie": movie.name, "number": resolved.number, "title": resolved.title, "path": str(epdir), "segments": len(segs),
            "ok": sum(1 for s in segs if s["status"] == "ok"), "needs_review": [s["id"] for s in segs if s["status"] == "needs-review"],
            "usage": state["usage"], "state": state}


def revise_segment(opts: Options, console: Console, llm: LLM, movie_name: str, episode: int, seg_id: str, note: str) -> dict:
    lib = Library(opts.output)
    found = lib.find_movie(movie_name)
    if not found:
        raise ValueError("No movie called %r in %s. Existing movies: %s" % (movie_name, opts.output, ", ".join(lib.movies()) or "none"))
    movie = lib.open_movie(found)
    epdir = movie.find_episode(episode)
    state = read_json(epdir / "episode.json") if epdir else None
    if not state:
        raise ValueError("Episode %d of %s was not found." % (episode, found))
    segs = state["segments"]
    idx = next((i for i, s in enumerate(segs) if s["id"].lower() == seg_id.lower()), None)
    if idx is None:
        raise ValueError("No clip %s. Clips: %s" % (seg_id, ", ".join(s["id"] for s in segs)))
    seg = segs[idx]
    notes = {n.get("scene"): n for n in (state.get("analysis") or {}).get("scenes", [])}
    prev_seg = segs[idx - 1] if idx > 0 and seg["mode"] in ("extend", "new-chain") else None
    nxt = segs[idx + 1] if idx + 1 < len(segs) else None
    console.say("Revising %s ..." % seg["id"])
    result = write_segment(seg, movie, notes.get(seg["scene"]), prev_seg, nxt, llm, console, opts, revision=note)
    seg.update({k: result[k] for k in ("prompt", "shots", "brief", "carry_over", "assumptions", "warnings", "errors", "timing", "status", "last_line", "last_speaker", "attempts")})
    folder = EpisodeFolder(epdir)
    state["updated"] = now_iso()
    save_segment_files(folder, seg, notes.get(seg["scene"]), movie, False)
    save_episode_files(folder, state, bool(state.get("offline")))
    follow = [s["id"] for s in segs[idx + 1:idx + 2] if s["mode"] in ("extend", "new-chain")]
    return {"clip": seg["id"], "status": seg["status"], "path": str(epdir), "timing": seg["timing"], "check_next": follow}
