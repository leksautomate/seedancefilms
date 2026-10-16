# How the agent works

`studio.py` is a real agent program. It writes prompts only and never generates video: you paste each prompt into Seedance 2.5 yourself. You paste a script, it talks to a language model through tool calls, and it
files everything under `output/`. This page explains what happens, where the checks are, and how to change things.

```
paste a script
   |
   v
[1] Intake ........... which movie? which episode?  (asks you when the movie is not given)
   |
   v
[1b] Script reader ... a production-layout script is read directly (scenes, planned seconds, lists)   (code, no model)
   |
   v
[2] Segmenter ........ scenes -> clips of up to 30 s, extension or new chain beyond, short clips  (code, no model)
   |
   v
[3] Analyst agent .... reads the whole episode: spine, why each scene earns its place,        (model, 1 loop)
   |                   characters, voices, tags, colour script, risks, unknowns
   v
[3b] Sheet writers ... one loop per character and per location; code renders the skill's        (model, 1 loop each)
   |                   template, checks it, and names the files @Name.md
   v
[4] Writer agents .... one loop per clip. The model calls tools:                              (model, 1 loop per clip)
   |                     lookup_camera_recipe  -> the camera engine's recipe and shot flow
   |                     check_prompt          -> linter + timing estimate, nothing saved
   |                     submit_segment_prompt -> saved ONLY if the linter passes
   |                     ask_user              -> one question, only if a missing fact changes the clip
   v
[5] Library .......... output/<Movie>/<Episode>/<Scene>/ files, plan.html, README, review checklist
```

Progress is written after every clip. If a run stops (network, Ctrl-C), run the same command again and it resumes.

## Seedance 2.5

The agent writes prompts for Seedance 2.5 and plans around its limits. Checked against the model's input schema:

| Setting | Limit |
|---|---|
| Duration | Whole seconds, 4 to 30, in one generation |
| Aspect ratio | 16:9, 4:3, 1:1, 3:4, 9:16, 21:9, adaptive |
| Resolution | 480p, 720p, 1080p |
| Audio | On by default: dialogue, ambience and lip-sync are generated with the video |
| Prompt length | Up to 30000 characters |
| References | Images, videos and audio files (up to 30 images, 10 videos and 10 audio files, per the model description) |

So by default a whole scene is one clip of up to 30 seconds, requested at the scene's own length. Use `--clip 15` for
shorter generations. Each clip's brief has a **Seedance 2.5 settings** section (duration, aspect ratio, resolution,
audio, inputs) so you know what to set when you generate it. Settings such as `aspect_ratio`, `resolution` and
`generate_audio` live in `output/<Movie>/movie.json`.

Not confirmed: how long an extension may be (the 60 second chain is an assumption), and whether your provider lets a
first-frame image be combined with reference images (the brief for a new chain says what to do if it does not).

## Character and location sheets

After the analysis, the agent builds the reference-image prompts from the `character-location-extractor-builder` skill
(`seedance_agent/sheets.py`, instructions in `prompts/sheet_writer.md`). It needs a visual style (`--visual-style`, or it
asks). For each core character and location the model fills structured fields through `submit_sheet`; code renders the
skill's template, so the numbered sections never drift and no placeholder is left. A sheet is checked for:

| Check | Why |
|---|---|
| All required fields, `@PascalCase` tag, 4 or more real HEX codes | The prompt is concrete and the file names match the images |
| One character per prompt, no other character named; no people on a location sheet | The skill's rules |
| The chosen style is in the prompt, no brackets | Paste-ready |
| Voice design prompt only for a character in more than one scene, or the lead | The skill's rule, decided by code from the script |
| Voice rules: language and "slight/thick" accent first, "Studio quality", no effect words, a preview text of at least 100 characters taken word for word from the character's own lines | ElevenLabs voice design practice |

Anything the script does not state is marked `(proposed)`. Extras with no image (a dealer, a buyer, guards) get no sheet;
the scene prompts describe them in full instead. The sheet tags become the bible tags, so every scene prompt names the
same images. `--sheets skip` leaves them out, `--sheets only` stops after them.

## Scene prompts under the studio rules

When the movie settings set `visual_style` and `language_lock` (the `--prompts` route can set them), the linter also
requires one `Visual Style:` line and the three English-language lock lines, directly under it. Shots carry timestamps
(`SHOT 2 (00:03-00:07) ...`) that start at 00:00 for each clip. A character marked `no_image` must be described in the
prompt, and a tag matches only as a whole word (`@Ali` is not found in `@AliBaba`).

## Prompts written outside the program

`--prompts prompts.json` files prompts that someone else wrote (for example an assistant working from the script),
through the same checks, once and without retries. The file has `prompts` (by clip id), optional `analysis`, `sheets`
and `settings`. This is how the worked example in `examples/ain-jalut-ep02/` was built. `--plan-only` writes the
segmentation and the plan page with no prompts, which is the first step of that route; `--wps 2.5` sets the speaking
rate for solemn drama (the pooled default is 3.4 words per second).

## What gets saved

```
output/
  The Six/                              the movie
    movie.json                          settings + the bible (characters, voices, tags, locations), shared by every episode
    Episode 01 - The Six/               the episode
      script.txt                        the script exactly as pasted
      plan.html                         the visual plan: scrubber, scene cards, prompts with copy buttons
      README.md                         production sheet: order, spine, colour script, risks, unknowns, assembly notes
      prompts-all.md                    every prompt in order, ready to copy
      review-checklist.md               what to check on each generated clip
      episode.json                      the full state (used to resume)
      characters-and-locations.md       the lists shown before the sheet prompts
      characters/@Qutuz.md              a character sheet prompt (+ VOICE DESIGN PROMPT for a recurring character)
      locations/@CitadelWall.md         a location sheet prompt
      images/characters/, images/locations/   empty, for the images made from those prompts
      Scene 01 - Kitchen/               a scene
        S01a_generate.txt               paste-ready prompt
        S01a_brief.md                   shot brief: purpose, stability constraints, shots, must-get moments, carry-over
        S01b_extend.txt                 the extension prompt
        S01b_brief.md
      _history/<timestamp>/...          earlier versions of any file that was replaced
```

The movie name is required. If the script has no `MOVIE:` line and you did not pass `--movie`, the agent asks, and
lists the movies that already exist so a new episode lands in the right place.

## The checks a prompt must pass

Every prompt goes through the same linter before it is saved. These are errors (the model must fix them):

| Check | Why |
|---|---|
| Spoken lines match the script **word for word, in order**, nothing added or dropped | The agent never rewrites your dialogue |
| Header says "Use ONLY hard cuts" and "NO music" | House style |
| Shots numbered 1..N, 2 to 14 shots, no placeholders such as `<name>` | Prompt must be paste-ready |
| Explicit ending (`END HERE.` or `CUT TO BLACK.`) | House style |
| Every speaker has a voice block (new generations) | Voice consistency |
| Tags for every character (new generations; extensions carry the designs in the source video) | Binds your uploaded references |
| An extension starts with "Extend ..." and quotes the previous clip's last spoken line | Continuity |
| Estimated running time not over the clip length | Fits the generation |
| With `language_lock`: the `[Negative: ...]` and `[System: Language: English] [Audio: English Speech]` lines, and one `Visual Style:` line | The studio's Seedance rules |

Warnings are saved with the prompt and shown on the plan page. If a model cannot fix an error in `--max-attempts` tries
(default 4), the best attempt is saved with the status `needs-review` and the open problems are written in the brief and
the README. If the model never submits anything, a labelled template draft is saved so the episode is never lost.

## Revising a clip

```
python3 studio.py revise --movie "The Six" --episode 1 --clip-id S01b "make the last shot a wide"
```

The same agent loop runs with your note and the current prompt, under the same checks. The old version moves to
`_history`. Dialogue cannot be changed this way, because it comes from the script. Change the script and run again.

## Choosing the model

Plain HTTP, no packages to install.

| Set | Effect |
|---|---|
| `ANTHROPIC_API_KEY` | Uses the Anthropic API (default model `claude-sonnet-5-5`) |
| `OPENAI_API_KEY` | Uses an OpenAI-compatible API (default model `gpt-4.1`) |
| `SEEDANCE_MODEL`, `--model` | Pick the model |
| `OPENAI_BASE_URL`, `--base-url` | Point at OpenRouter, a local server, and so on |
| `--offline` | No model. Builds template drafts from the script so you can see the structure |

## Where to change behaviour

| To change | Edit |
|---|---|
| How prompts are written (house style, camera rules, process) | `seedance_agent/prompts/writer.md` |
| How the story is analysed | `seedance_agent/prompts/analyst.md` |
| How the character and location sheets are written and checked | `seedance_agent/prompts/sheet_writer.md`, `seedance_agent/sheets.py` |
| How a production-layout script is read | `seedance_agent/script_doc.py` |
| What counts as an error or warning | `seedance_agent/lint.py` |
| Timing numbers (words per second, shot lengths) | `.claude/skills/*/scripts/*.py` (one source for the agent and the skills) |
| How scenes are split into clips | `.claude/skills/episode-segmenter/scripts/segment_episode.py` |
| The bible: tags, voices, looks, style lock | `output/<Movie>/movie.json` (your edits are kept; the agent only fills blanks) |

## Tests

```
python3 -m unittest discover -s tests -t .
```

Over 100 tests cover intake, the folder structure and versioning, the linter, the script reader, the sheets (render, checks, a scripted model writing
them), both model clients (against mocked HTTP), the agent loop, and the whole pipeline including a scripted model that first changes a line of dialogue
and has to fix it. The worked example under `examples/` is filed and checked end to end, and its 325 spoken words are compared with the script.

## What has not been run

The model clients were tested against mocked HTTP responses, not against the live services. No real model has written a
prompt or sheet through this code yet. The first run with a real key is the first real test of prompt quality; if a prompt comes
back weak, the fix is almost always in `prompts/writer.md`.
