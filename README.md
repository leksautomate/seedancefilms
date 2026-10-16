# Seedance Studio

Paste an episode script. The agent splits it into clips, writes a checked Seedance prompt for every clip, and files
everything under `output/<Movie>/<Episode>/<Scene>/`.

**It only writes prompts. It never generates video.** You paste each prompt into Seedance 2.5 yourself. The only network calls
the program makes are to the language model that writes the prompts.

```
python3 studio.py
```

Then paste your script and finish with a line containing only `END`. If it does not say which movie the episode belongs
to, the agent asks, so every episode is filed under its movie.

## Set up

Python 3.9 or newer (tested on 3.13). Nothing to install.

```
export ANTHROPIC_API_KEY=...        # or OPENAI_API_KEY (and optionally OPENAI_BASE_URL, SEEDANCE_MODEL)
python3 studio.py                   # paste a script
python3 studio.py script.txt --movie "The Six"
python3 studio.py revise --movie "The Six" --episode 1 --clip-id S01b "make the last shot a wide"
python3 studio.py list
python3 studio.py script.txt --movie "The Six" --offline     # no model: template drafts, to see the structure
python3 studio.py script.txt --visual-style "2D anime"       # also build the character and location sheets
python3 studio.py script.txt --plan-only --wps 2.5           # only split the script and write the plan (slow, solemn drama: 2.5 words/s)
python3 studio.py script.txt --prompts prompts.json          # file prompts written elsewhere, through the same checks
```

## What you get

```
output/
  The Six/
    movie.json                       settings + bible (characters, voices, tags) shared by all episodes
    Episode 01 - The Six/
      plan.html                      visual plan: runtime scrubber, scene cards, prompts with copy buttons
      README.md                      production sheet: spine, colour script, risks, unknowns, assembly notes
      prompts-all.md                 every prompt in order
      review-checklist.md            what to check on each generated clip
      characters-and-locations.md    the lists, shown before the sheet prompts, with anything not in the script marked (proposed)
      characters/@Qutuz.md           one character sheet prompt (+ voice design prompt for a recurring character)
      locations/@CitadelWall.md      one location sheet prompt
      images/characters/             empty: put the generated images here, named like the prompt files
      images/locations/
      Scene 01 - Kitchen/
        S01a_generate.txt            paste-ready prompt
        S01a_brief.md                shot brief for that clip
        S01b_extend.txt              the extension prompt
```

The character and location sheets follow the `character-location-extractor-builder` skill: the script is the only source
of truth, anything added is marked `(proposed)`, one character or location per prompt, and a voice design prompt only for
a character who appears in more than one scene or leads the series. Scene prompts then use the same `@Name` tags, a single
`Visual Style:` line, the English-language lock lines, timed shots, and a full description for anyone who has no image.
Set the style with `--visual-style`; if it is missing and you are at a terminal, the agent asks.

A script in the production layout (header, RUNTIME MAP, CLIP and SCENE blocks) is read directly: scenes, the planned
seconds, on-screen text added in the edit, the character and location lists. A worked example with its prompts and
sheets is in [`examples/ain-jalut-ep02/`](examples/ain-jalut-ep02/).

Prompts are written for Seedance 2.5, which renders 4 to 30 seconds in one generation, so by default a whole scene is one clip (use `--clip 15` for shorter ones). Every prompt is checked before it is saved: your dialogue word for word, hard cuts only, no music, voices, tags, an
explicit ending, and an estimated running time that fits the clip. Details: [`docs/agent-pipeline.md`](docs/agent-pipeline.md).
What was learned from other projects and what is original: [`docs/design.md`](docs/design.md).

## The skills

The same knowledge is also available as skills for an AI assistant, in `.claude/skills/`:
`episode-segmenter`, `cinematic-camera-engine` (English adaptation of
[yzsp-studio/cinematic-camera-engine](https://github.com/yzsp-studio/cinematic-camera-engine), MIT) and
`seedance-scene-prompter`. The agent uses their scripts and reference files directly, so there is one source of truth.

## Tests

```
python3 -m unittest discover -s tests -t .
```
