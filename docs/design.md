# Design: what was learned, and what is original

Three open-source projects (all MIT) were studied before this agent was designed, plus the camera engine already
adapted in `.claude/skills/cinematic-camera-engine`. Ideas were taken, not code. Where text was adapted it is credited.

## What each project taught

### cinema-skills (Benjamin Leleu): https://github.com/Benitoow/cinema-skills
Five plain `SKILL.md` files: shot list, scene breakdown, colour script, cut list, export checklist.

| Lesson | Where it lives here |
|---|---|
| Never invent. Work only from the text and list gaps as unknowns | Analyst and writer rules; the dialogue linter; `unknowns` and `assumptions` in the README |
| Ask once, at most three questions, otherwise state the assumption in one line | `ask_user` has a budget of one question per task |
| Working documents, not essays: tables and lists | `README.md`, `*_brief.md` |
| "Must-get shots" and "if time runs out, cut this first" | Fields in every clip brief |
| Colour script: palette and grade per beat, a motif, continuity warnings | `color_script` and `motif` in the analysis, written to the README |
| Scene breakdown: risks with a cheaper alternative | `risks` in the analysis |
| Export checklist and "verify against current specs" | Assembly notes in the README |

### ai-video-shot-brief-template (SceneVela): https://github.com/liubrain39/ai-video-shot-brief-template
A shot brief and an output review checklist for one AI-video clip.

| Lesson | Where it lives here |
|---|---|
| Separate what the subject does from what the camera does; one of each per shot | Writer rule 7; the brief's Subject action and Camera fields |
| A "stability constraints" field: what must not change | Brief field, plus the closing IMPORTANT block in every prompt |
| Review the output against the brief with blocking checks and an issue log, not one score | `review-checklist.md` |
| Decisions: ACCEPT, ITERATE, REJECT, PUBLISH HOLD, and change one variable at a time | `review-checklist.md` |
| Reference assets need confirmed rights | The Reference assets section of every brief |

### film-plan (Seyon Vasantharajan): https://github.com/seyonv/film-plan
A film plan as a page, with a chat rail that edits it.

| Lesson | Where it lives here |
|---|---|
| A film is time, so show time: a scrubber of the whole runtime | The strip across the top of `plan.html`, one block per clip, as wide as its length |
| Find the spine (acts) before the scenes | The analyst builds the acts first; the plan page groups clips under them |
| "Why this scene earns its place" is the plan's conscience, and may honestly say "not yet earned" | The `why` field, shown in red when the analyst cannot justify a scene |
| Honest build state per scene (new, keep, stub) | `status` (ready or stub) in the scene notes; ok / needs-review / pending per clip |
| Everything on the page derives from one data file | `plan.html`, README and `prompts-all.md` are all rendered from `episode.json` |
| A validation gate before a change lands, and a rollback if it fails | The prompt linter; a rejected prompt is never saved |
| Edit by talking, every change versioned and undoable | `studio.py revise`, and `_history/` |

### cinematic-camera-engine (yzsp-ai): https://github.com/yzsp-studio/cinematic-camera-engine
Scene type and mood to a shot plan. Adapted into English in `.claude/skills/cinematic-camera-engine` and exposed to the
agent as the `lookup_camera_recipe` tool.

## What is original here

1. **The movie, episode and scene library.** One movie folder holds a **bible** (characters, voices, tags, locations, style)
   that every episode reuses, so a character keeps the same tag and voice from episode 1 to episode 20. Your edits to the
   bible are never overwritten. The agent asks for the movie name instead of guessing it.
2. **Clips, not just scenes.** The segmenter turns a scene into the right chain of Seedance generations (15 s, +15 s
   extension, new chain, merged short scenes) and picks cut points at the end of an exchange, never mid-line, never mid-motion.
3. **Timing from measured data.** Speaking rate (3.4 words per second), shot length (1.7 to 2.7 s) and words per 15 s
   (16 to 26) were measured on five published clips with Whisper transcripts, and feed both the segmenter and the linter.
4. **The dialogue guard.** The linter compares the prompt's spoken words with the script's, in order. A model that
   rewords a line is rejected and has to correct itself. None of the studied projects can guarantee this.
5. **House style as an enforced contract.** Hard cuts only, no music, voice blocks, tags, SAME-voice, explicit endings and
   extension quoting are checked in code, not only requested in a prompt.
6. **An agent with gated tools.** The model cannot save a prompt that fails the checks, cannot change dialogue, and
   cannot skip a clip. A clip it cannot fix is saved for review rather than lost, and a run resumes after an interruption.
7. **Sheets rendered by code from model-written fields.** The character and location sheet prompts follow the studio's own
   skill. The model supplies facts; code renders the template and checks it (one character per prompt, real HEX codes,
   voice design only for recurring characters, preview text taken from the character's own lines). The script stays the
   only source of truth, and every invented detail is marked `(proposed)`.
8. **Reading a production script as it is written.** Runtime maps, clip blocks, on-screen text and the character and
   location lists are read directly, so planned seconds and edit-room text are kept apart from what Seedance generates.
9. **Provider neutral, zero dependencies.** Anthropic or any OpenAI-compatible endpoint over plain HTTP, and an
   `--offline` mode for template drafts.

## Honest limits

- No real model has written a prompt or a sheet through this code. Everything else is tested.
- The visual style of the worked example ("2D anime") was inferred from the skill text, not stated by the script.
- Timing numbers rest on five clips and one prompt matched to its clip.
- Seedance 2.5's duration range (4 to 30 seconds) is confirmed from its input schema. The 60 second chain (a generation plus one extension) is an assumption, and so is whether a provider allows a first-frame image together with reference images.
- The offline drafts are templates. They show the structure and pass the checks, but they are not creative writing.
