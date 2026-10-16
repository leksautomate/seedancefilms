"""Turns the episode state into the files a person reads and copies from (all plain Markdown or text)."""
from __future__ import annotations

import re

from .library import scene_folder_name

MODE_HELP = {
    "single": "Generate this clip on its own.",
    "generate": "Generate this clip first. Its extension follows.",
    "extend": "Upload the previous clip's result and use this as the extension prompt (it starts from that clip's exact final frame).",
    "new-chain": "Start a new generation from the last frame of the previous clip, used as the first-frame reference.",
}


def seg_files(seg: dict) -> tuple[str, str, str]:
    folder = scene_folder_name(seg["scene"], seg.get("heading", ""), seg.get("location", ""), seg.get("scene_title"))
    base = "%s_%s" % (seg["id"], seg["mode"])
    return folder, "%s.txt" % base, "%s_brief.md" % seg["id"]


def generation_settings(seg: dict, settings: dict) -> list[str]:
    """What to set in Seedance 2.5 for this clip (limits checked against the model's input schema)."""
    secs = max(4, min(30, int(round(seg.get("request_s") or settings.get("clip_seconds", 30)))))
    mode = seg["mode"]
    aspect = settings.get("aspect_ratio", "16:9")
    lines = ["- **Model:** %s" % settings.get("video_model", "Seedance 2.5"),
             "- **Duration:** %d seconds (the model takes whole seconds from 4 to 30)" % secs,
             "- **Aspect ratio:** %s" % ("adaptive (the first-frame image sets the shape)" if mode == "new-chain" else aspect),
             "- **Resolution:** %s (480p is cheaper for a test render)" % settings.get("resolution", "1080p"),
             "- **Audio:** %s (dialogue, ambience and lip-sync are generated with the video)" % ("on" if settings.get("generate_audio", True) else "off")]
    if mode == "extend":
        lines.append("- **Inputs:** the previous clip's video as the video reference, plus the character and location references. Paste the extension prompt.")
    elif mode == "new-chain":
        lines.append("- **Inputs:** the previous clip's last frame as the first-frame image, plus the references. Some providers do not allow a first-frame image together with reference images; if yours does not, add the last frame as a normal reference image and keep the prompt as written.")
    else:
        lines.append("- **Inputs:** the reference images for the tags listed below (a model takes up to 30 images, 10 videos and 10 audio files), and optionally an audio file to fix a character's voice. Paste the prompt.")
    return lines


def _bullets(items) -> str:
    return "\n".join("- %s" % i for i in items) if items else "- (none)"


def brief_md(seg: dict, scene_note: dict | None, settings: dict, offline: bool) -> str:
    b = seg.get("brief") or {}
    t = seg.get("timing") or {}
    c = seg.get("carry_over") or {}
    lines = ["# %s — %s · %s" % (seg["id"], seg.get("heading", ""), seg["mode"]),
             "",
             "Status: **%s**%s · estimated %.1fs, request %ds · %d spoken lines, %d words · part %d of %d" % (
                 seg.get("status", "pending").upper(), " (offline draft, no model used)" if offline else "", seg.get("estimated_s", 0),
                 seg.get("request_s", 0), seg.get("dialogue_lines", 0), seg.get("dialogue_words", 0), seg.get("part", 1), seg.get("parts", 1)),
             "", "## How to generate", "", MODE_HELP.get(seg["mode"], ""), "",
             "## Seedance 2.5 settings", ""] + generation_settings(seg, settings) + [""] + (
                 ["## Added in the edit (not generated)", ""] + ["- On-screen text: %s" % t for t in seg["overlays"]] + [""] if seg.get("overlays") else [])
    if scene_note:
        lines += ["## Why this scene earns its place", "", scene_note.get("why", "(not analysed)"), ""]
    lines += ["## Shot brief", "",
              "- **Purpose of the clip:** %s" % (b.get("purpose") or "-"),
              "- **Subject:** %s" % (b.get("subject") or "-"),
              "- **Subject action:** %s" % (b.get("subject_action") or "-"),
              "- **Camera:** %s" % (b.get("camera") or "-"),
              "- **Environment:** %s" % (b.get("environment") or "-"),
              "- **Lighting:** %s" % (b.get("lighting") or "-"),
              "- **Visual direction:** %s" % (b.get("visual_direction") or "-"),
              "- **Aspect ratio:** %s" % settings.get("aspect_ratio", "16:9"),
              "", "**Stability constraints (must not change):**", "", _bullets(b.get("stability")), ""]
    shots = seg.get("shots") or []
    if shots:
        lines += ["## Shots", "", "| # | Scale | Angle | Camera | Seconds | Job | Spoken line |", "|---|---|---|---|---|---|---|"]
        for s in shots:
            lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                s.get("n", ""), s.get("scale", ""), s.get("angle", ""), s.get("camera", ""), s.get("seconds", ""),
                str(s.get("function", "")).replace("|", "/"), str(s.get("dialogue") or "").replace("|", "/")))
        lines.append("")
    lines += ["## Must-get moments", "", _bullets(b.get("must_get")), "",
              "## If the generation runs long, cut first", "", _bullets(b.get("cut_first")), "",
              "## Carry over to the next clip", "",
              "- **Last frame:** %s" % (c.get("last_frame") or "-"),
              "- **Positions:** %s" % (c.get("positions") or "-"),
              "- **Props:** %s" % (c.get("props") or "-"),
              "- **Costume state:** %s" % (c.get("costume") or "-"),
              "- **Lighting:** %s" % (c.get("lighting") or "-"), "",
              "## Reference assets", "",
              "Upload the references behind these tags: %s." % (", ".join(seg.get("tags", [])) or "none listed"),
              "Use only assets you own or are authorised to use.", "",
              "## Assumptions", "", _bullets(seg.get("assumptions")), ""]
    if seg.get("errors"):
        lines += ["## Open problems (the prompt was saved for review)", "", _bullets(seg["errors"]), ""]
    lines += ["## Warnings", "", _bullets(seg.get("warnings")), "",
              "## Timing check", "",
              "Estimated %.1fs of a %ds clip (%s). Speech %.1fs. These are estimates: speech runs about 3.4 words per second and a shot with a line runs about a second longer than the speech." % (
                  t.get("estimated_s", 0), t.get("limit_s", settings.get("clip_seconds", 30)), t.get("verdict", "n/a"), t.get("speaking_s", 0)), ""]
    return "\n".join(lines)


def prompts_all_md(state: dict) -> str:
    out = ["# %s — Episode %02d%s" % (state["movie"], state["number"], (" — " + state["title"]) if state.get("title") else ""),
           "", "All prompts in generation order. Copy each block as it is.", ""]
    for seg in state["segments"]:
        out += ["---", "", "## %s · %s · %s · %s" % (seg["id"], seg.get("heading", ""), seg["mode"], seg.get("status", "pending")),
                "", MODE_HELP.get(seg["mode"], ""), ""]
        if seg.get("prompt"):
            out += ["```text", seg["prompt"].rstrip(), "```", ""]
        else:
            out += ["(no prompt yet)", ""]
    return "\n".join(out)


def readme_md(state: dict, offline: bool) -> str:
    a = state.get("analysis") or {}
    total = sum(s.get("estimated_s", 0) for s in state["segments"])
    title = "%s — Episode %02d%s" % (state["movie"], state["number"], (" — " + state["title"]) if state.get("title") else "")
    lines = ["# %s" % title, "", "Production sheet. Prompts are in the scene folders and in `prompts-all.md`. Open `plan.html` for the visual plan.", ""]
    if offline:
        lines += ["> These prompts are offline drafts built from a template. No model was used.", ""]
    if a.get("logline"):
        lines += ["**Logline:** %s" % a["logline"], ""]
    if a.get("tone"):
        lines += ["**Tone:** %s" % a["tone"], ""]
    lines += ["## Clips in order", "", "| Clip | Scene | Mode | Plan s | Est. s | Request s | Lines | Words | Status |", "|---|---|---|---|---|---|---|---|---|"]
    for s in state["segments"]:
        plan = ("%d" % s["planned_s"]) if s.get("planned_s") and s.get("part", 1) == 1 else ""
        lines.append("| %s | %s | %s | %s | %.1f | %d | %d | %d | %s |" % (s["id"], s.get("scene_title") or s.get("heading", ""), s["mode"], plan, s.get("estimated_s", 0),
                                                                          s.get("request_s", 0), s.get("dialogue_lines", 0), s.get("dialogue_words", 0), s.get("status", "pending")))
    st = state.get("settings", {})
    lines += ["", "Estimated runtime: **%.1fs** (%.1f min) in %d clips." % (total, total / 60, len(state["segments"])),
              "", "Generate every clip with %s at %s, %s, audio %s. Each clip's brief lists its duration (whole seconds, 4 to 30) and inputs." % (
                  st.get("video_model", "Seedance 2.5"), st.get("aspect_ratio", "16:9"), st.get("resolution", "1080p"),
                  "on" if st.get("generate_audio", True) else "off"), ""]
    sd = state.get("script_doc") or {}
    if sd:
        lines += ["## Not generated (edit room)", ""]
        if sd.get("opening"):
            lines.append("- Opening: %s" % sd["opening"])
        for s in state["segments"]:
            if s.get("overlays") and s.get("part", 1) == 1:
                lines.append("- Scene %s on-screen text: %s" % (s["scene"], "; ".join(s["overlays"])))
        if sd.get("end_card"):
            lines.append("- End card: %s" % sd["end_card"])
        if sd.get("runtime_s"):
            span = re.search(r"(\d+):(\d{2})\s*-\s*(\d+):(\d{2})", sd.get("end_card") or "")
            end_s = (int(span.group(3)) * 60 + int(span.group(4))) - (int(span.group(1)) * 60 + int(span.group(2))) if span else 0
            open_s = next((b.get("seconds") or 0 for b in sd.get("blocks", []) if "opening" in b.get("block", "").lower()), 0)
            plan_gen = sd["runtime_s"] - open_s - end_s
            est = sum(s.get("estimated_s", 0) for s in state["segments"])
            lines += ["", "Runtime plan: %ds in all, so %ds of generated video once the %ds opening and the %ds end card are taken out. "
                      "Estimated generated video: %.0fs in %d clips." % (sd["runtime_s"], plan_gen, open_s, end_s, est, len(state["segments"]))]
        lines.append("")
        if sd.get("notes"):
            lines += ["## Production notes (from the script)", ""] + ["- %s" % n for n in sd["notes"]] + [""]
    if a.get("spine"):
        lines += ["## The spine", ""]
        for act in a["spine"]:
            lines.append("- **%s** (scenes %s): %s" % (act.get("act", ""), ", ".join(str(x) for x in act.get("scenes", [])), act.get("note", "")))
        lines.append("")
    notes = {n.get("scene"): n for n in a.get("scenes", [])}
    if notes:
        lines += ["## Scene notes", "", "| Scene | Type | Mood | Build state | Why it earns its place |", "|---|---|---|---|---|"]
        for k in sorted(notes):
            n = notes[k]
            lines.append("| %s | %s | %s | %s | %s |" % (k, n.get("scene_type", ""), n.get("mood", ""), n.get("status", ""), str(n.get("why", "")).replace("|", "/")))
        lines.append("")
    if a.get("color_script"):
        lines += ["## Colour script", ""]
        if a.get("motif"):
            lines += ["**Motif:** %s" % a["motif"], ""]
        lines += ["| Beat | Emotion | Dominant | Accent | Contrast | Saturation | Swatches |", "|---|---|---|---|---|---|---|"]
        for r in a["color_script"]:
            lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (r.get("beat", ""), r.get("emotion", ""), r.get("dominant", ""), r.get("accent", ""),
                                                                 r.get("contrast", ""), r.get("saturation", ""), " ".join(r.get("hex", []))))
        lines += ["", "Hex swatches are suggestions for reference boards. Check them on a generated still before relying on them.", ""]
    if a.get("risks"):
        lines += ["## Risks", ""]
        for r in a["risks"]:
            lines.append("- **%s.** %s%s" % (r.get("item", ""), r.get("why", ""), (" Cheaper alternative: %s" % r["alternative"]) if r.get("alternative") else ""))
        lines.append("")
    if a.get("unknowns"):
        lines += ["## Unknowns (not in the script)", "", _bullets(a["unknowns"]), ""]
    if a.get("assumptions"):
        lines += ["## Assumptions made", "", _bullets(a["assumptions"]), ""]
    review = [s for s in state["segments"] if s.get("status") == "needs-review"]
    if review:
        lines += ["## Needs your review", ""]
        for s in review:
            lines.append("- **%s**: %s" % (s["id"], "; ".join(s.get("errors") or ["see the brief"])))
        lines.append("")
    lines += ["## Assembly notes", "",
              "- Generate in the order above. An `extend` clip starts from the previous clip's exact final frame.",
              "- When joining a generation and its extension in an editor, cut where the extension begins so no frame repeats.",
              "- Keep one loudness target across all clips. Streaming platforms commonly normalise near -14 LUFS with true peak around -1 dBTP. Verify against the destination's current specs.",
              "- Run `review-checklist.md` on every generated clip before it goes into the edit.", ""]
    return "\n".join(lines)


def review_md(state: dict) -> str:
    ids = [s["id"] for s in state["segments"]]
    lines = ["# Review checklist — %s, Episode %02d" % (state["movie"], state["number"]), "",
             "Use this on each generated clip, next to its brief. It records a human review of one clip. A clip that renders is not a clip that passes. "
             "(Structure adapted from the SceneVela AI video output review checklist, MIT licensed.)", "",
             "## For every clip", "",
             "### 1. The file", "- [ ] Plays from start to finish; duration and orientation are right", "- [ ] No frozen, blank or duplicated frames", "- [ ] Audio is present and not clipped",
             "", "### 2. Matches the brief", "- [ ] Every spoken line is the script's line, in order, in the right voice", "- [ ] Hard cuts only: no tracking, slides or whip pans",
             "- [ ] No music", "- [ ] Each shot does the one job the brief gave it", "- [ ] Every stability constraint holds",
             "", "### 3. Continuity", "- [ ] Each character's design, clothing and proportions match the references and the previous clip",
             "- [ ] Left/right positions and props match the brief's carry-over", "- [ ] Lighting and colour match the rest of the scene",
             "- [ ] No unintended text, logo, watermark or extra person",
             "- [ ] The last frame is stable enough to extend from (when an extension follows)", "",
             "### 4. Rights and disclosure", "- [ ] Every reference asset is owned or authorised",
             "- [ ] Any AI-generated-content disclosure the destination requires is ready", "",
             "## Decision for each clip", "",
             "ACCEPT: all checks pass. ITERATE: usable, one named change needed. REJECT: misses the brief. PUBLISH HOLD: permission or disclosure still missing.", "",
             "| Clip | Decision | Issues (timecode, what you see) | Single change to try next |", "|---|---|---|---|"]
    for i in ids:
        lines.append("| %s | | | |" % i)
    lines += ["", "Change one variable at a time between attempts, so you can tell what fixed it.", ""]
    return "\n".join(lines)
