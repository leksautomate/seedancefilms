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
[2] Segmenter ........ scenes -> clips of up to 30 s, extension or new chain beyond, short clips  (code, no model)
   |
   v
[3] Analyst agent .... reads the whole episode: spine, why each scene earns its place,        (model, 1 loop)
   |                   characters, voices, tags, colour script, risks, unknowns
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
| What counts as an error or warning | `seedance_agent/lint.py` |
| Timing numbers (words per second, shot lengths) | `.claude/skills/*/scripts/*.py` (one source for the agent and the skills) |
| How scenes are split into clips | `.claude/skills/episode-segmenter/scripts/segment_episode.py` |
| The bible: tags, voices, looks, style lock | `output/<Movie>/movie.json` (your edits are kept; the agent only fills blanks) |

## Tests

```
python3 -m unittest discover -s tests -t .
```

65 tests cover intake, the folder structure and versioning, the linter, both model clients (against mocked HTTP), the
agent loop, and the whole pipeline including a scripted model that first changes a line of dialogue and has to fix it.

## What has not been run

The model clients were tested against mocked HTTP responses, not against the live services. No real model has written a
prompt through this code yet. The first run with a real key is the first real test of prompt quality; if a prompt comes
back weak, the fix is almost always in `prompts/writer.md`.
