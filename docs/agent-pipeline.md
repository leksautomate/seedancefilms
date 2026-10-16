# Episode-to-video agent pipeline

Goal: turn a full episode script into ready-to-generate Seedance prompts, one segment at a time, with the
dialogue checked against the clip length.

```
 episode script
      |
      v
 [1] episode-segmenter ........ scenes -> segments (15 s, +15 s extension, new chains, short clips)
      |                          output: segment plan (JSON + table)
      v
 [2] cinematic-camera-engine .. scene type + mood -> shot plan that fits the segment's seconds
      |                          output: SHOT N - SCALE - ANGLE list, color anchor
      v
 [3] seedance-scene-prompter .. shot plan + dialogue -> prompt text (full or extension style)
      |                          output: prompt block per segment
      v
 [4] dialogue_timing.py ....... counts spoken words, estimates seconds, FITS / TIGHT / TOO LONG
      |                          loop back to [3] if TOO LONG (trim, merge a shot, or split the segment)
      v
 approved prompts, in order, with the generation mode (generate / extend / new-chain)
```

Each stage is a skill in `.claude/skills/`. Stages [1] and [4] are scripts (`segment_episode.py`,
`dialogue_timing.py`), so the numbers are computed, not guessed. Stages [2] and [3] are instructions the model follows.

## Data contract between stages

Stage 1 writes this (the real output is in `episode-segmenter/examples/sample-segments.json`):

```json
{
  "id": "S01b",
  "scene": 1,
  "heading": "SCENE 1 - INT. KITCHEN - NIGHT",
  "mode": "extend",
  "estimated_s": 14.8,
  "request_s": 15,
  "characters": ["GIRL", "WOLF"],
  "scene_type_hint": "dialogue",
  "mood_hint": "neutral",
  "dialogue_lines": 5,
  "dialogue_words": 23,
  "last_beat": "You thought what?",
  "next_beat": "",
  "events": [{"kind": "dialogue", "speaker": "WOLF", "text": "Six? I thought you were, like, a TEN!", "words": 8, "seconds": 3.3}],
  "notes": ["extension: start from the exact final frame of the previous segment"]
}
```

Stage 2 adds `shots`: a list of `{scale, angle, movement, seconds, function, prompt_fragment}`.
Stage 3 adds `prompt` (text) and stage 4 adds `timing` (`lines`, `words`, `estimated_s`, `verdict`).

## State the agent keeps

| Item | Why |
|---|---|
| Tag registry (`@ TAG GIRL`, `@ TAG KITCHEN`, ...) | Tags bind the user's uploaded references to every prompt. Spelling must not drift. |
| Voice blocks per character | Reused verbatim, with "SAME voice" in each dialogue shot, across all segments and extensions |
| Color anchor | The first approved segment fixes the grade (see STEP 7 of the camera engine). Later segments reuse it |
| Continuity sheet per scene | Positions, props, costume state, lighting. Copied into each extension prompt |
| Last spoken line of each segment | The extension prompt quotes it |

## Human checkpoints

1. **Segment plan.** Show the table and the cut points. Approve before any prompt is written.
2. **First segment of each scene.** Approve the prompt, then generate. Its look becomes the anchor for the rest.
3. **TIGHT or TOO LONG segments.** The agent proposes a trim; a person decides.

Generation itself is outside these skills. Whoever runs the generator confirms credits and results.

## Running it by hand (no code needed)

1. Put the episode in `episode.txt` and ask Claude to "segment this episode". It runs the script and shows the plan.
2. Approve the plan.
3. Ask for "prompts for segment S01a". Claude uses the camera engine, writes the prompt and reports the timing table.
4. Generate, then ask for the next segment (`S01b`, an extension) and paste nothing else: the continuity details are in the plan.

## Building it as a standalone agent

The same stages can run as a program, using the Claude Agent SDK or the plain API with tools:

- Tools: `segment_episode` and `dialogue_timing` as local functions (they are plain Python with no dependencies beyond the standard library).
- System prompt: the text of the three `SKILL.md` files, loaded as skills or concatenated.
- Loop: per segment, call the model with the segment JSON, let it call `dialogue_timing`, and stop when the verdict is FITS or the model reports it cannot fit after trimming.
- Orchestration order is fixed by the data contract above, so it can be a simple script, not a free-form agent.

This repository does not contain that program yet. It is a short build once the skills are settled.

## Known limits

- Timing numbers come from five published clips and one prompt matched to its clip. They are estimates.
- The 4 second minimum generation and the 30 second chain are assumptions to confirm against the generator.
- The segmenter's parsing is heuristic. Unusual script formats may need a small cleanup before running it.
