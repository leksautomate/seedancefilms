---
name: episode-segmenter
description: Splits a full episode script into Seedance-sized segments - one scene per generation of up to 30 seconds (Seedance 2.5 renders 4 to 30 seconds in one go), longer scenes as a generation plus an extension or chained clips, and very short scenes merged or kept as short clips - with estimated seconds, dialogue word counts, cut points and hand-off notes for each segment. Use when the user gives an episode, script or story and wants it broken into scenes, clips, segments or shots to generate, asks how many seconds a scene will take, or asks what to do when a scene is too long or too short for one clip.
---

# Episode Segmenter

Turns an episode script into a **segment plan**: an ordered list of clips, each small enough for one Seedance
generation, with the cut points chosen so a split never lands in the middle of a line.

This is stage 1 of the pipeline in `docs/agent-pipeline.md`:

```
episode script
   -> episode-segmenter          (this skill: segment plan)
   -> cinematic-camera-engine    (shot plan for each segment)
   -> seedance-scene-prompter    (prompt text + dialogue timing check)
```

## The segmentation rules

A **segment** is one Seedance 2.5 generation. The model renders any whole number of seconds from 4 to 30 in a
single generation, so the default budget is 30 seconds per generation and a whole scene is normally one clip.
A generation can be extended once, so one scene can use up to 60 seconds in a single chain. Use `--clip 15` if you
prefer shorter generations (for example for dense dialogue).

| Estimated scene length | What to do | Segment mode |
|---|---|---|
| Shorter than 6 s | Merge into the next scene when both are in the same location. Otherwise keep it as a short clip and request only the seconds it needs (assumed minimum 4 s). | `single` (short) |
| 6 to 30 s | One generation, requested at the scene's own length (rounded up, with 10 percent slack) | `single` |
| 30 to 60 s | Generation plus one extension, cut at the end of a spoken exchange | `generate`, `extend` |
| Longer than 60 s | Several chains. Each new chain starts from the last frame of the previous one as a first-frame reference, cut at a natural beat. | `generate`, `extend`, `new-chain`, `extend`, ... |

Cut-point rules (the script applies these automatically):
1. Never cut inside one character's run of speech.
2. Prefer to cut after an exchange has finished. The next segment then starts on a new beat.
3. Do not end a segment on a frame mid-motion (a jump, a throw, a fall). An extension needs a stable last frame.
4. A cliffhanger or unanswered question is a good place to end a segment.
5. Keep each piece at least 5 seconds, so no segment is a stray fragment.

## Workflow

1. **Confirm the assumptions** with the user in one line, and ask only about what is missing: clip length (default 30 s), longest chain (default 60 s), words per second (default 3.4). Do not ask for anything already given.
2. **Save the script to a text file** and run the segmenter:
   ```
   python3 -I .claude/skills/episode-segmenter/scripts/segment_episode.py episode.txt
   python3 -I .claude/skills/episode-segmenter/scripts/segment_episode.py episode.txt --json
   ```
   Flags: `--clip`, `--chain`, `--min-clip`, `--wps`, `--line-gap`, `--action`, `--reaction`, `--detail`, `--establish`, `--tolerance`.
   The script reads scene headings (`SCENE 3`, `INT.`, `EXT.`), spoken lines (`NAME: text`, or the name alone on a line followed by the line, or quoted text inside an action line) and treats everything else as action beats.
3. **Review the plan with judgement.** The script is a first pass. Check:
   - scenes that change place or time halfway through but have no heading (split them by hand)
   - montages and establishing shots (they are short by design, merge them into the following scene if it helps)
   - a segment flagged `TIGHT` (estimate over the budget by a little): trim a line or merge a beat
   - cut points: read the `last_beat` and `next_beat` fields and confirm the frame is stable
4. **Produce the segment plan** in the format below and show it to the user. Wait for approval before generating prompts for a whole episode.
5. **For each approved segment**, hand off in this order:
   1. `cinematic-camera-engine`: scene type, mood, and a shot plan that fits the segment's seconds
   2. `seedance-scene-prompter`: the prompt text, and for `extend` segments the extension prompt that quotes the last spoken line of the previous segment
   3. `seedance-scene-prompter/scripts/dialogue_timing.py`: the final dialogue and timing check on the finished prompt

## Output format

Start with the summary table, then one card per segment.

```
| Segment | Scene | Mode | Est. s | Request s | Lines | Words | Cut after |
```

```
SEGMENT S01b  (scene 1, part 2 of 2, mode: extend)
Location:     INT. KITCHEN - NIGHT            @TAG: <location tag if the user has one>
Characters:   WOLF, GIRL                      @TAG: <character tags>
Estimated:    14.8 s    Request: 15 s
Scene type:   dialogue / comedic              (hint for cinematic-camera-engine)
Starts from:  exact final frame of S01a, after GIRL says "<last line of S01a>"
Beats:        1. <beat>  2. <beat>  ...
Dialogue:     5 lines, 23 words
Ends on:      <last beat, a stable frame>
Carry over:   positions, props, lighting, costume details that must match across the cut
Notes:        <TIGHT, short clip, new chain, anything the script flagged>
```

Keep the user's tag spelling exactly (`@ TAG GIRL`, `@TAG ROXIE`).

## Things to tell the user

- The estimates are conservative. In the sample the script stops the first kitchen clip after four lines, while the real published clip carried six lines in 15 seconds. The final check with `dialogue_timing.py` on the written prompt is tighter than the segmenter. If it says FITS with room to spare, the cut can move later.
- Timing rests on measured numbers from published clips (see `seedance-scene-prompter/references/measured-clips.md`): 3.4 words per second of speech, shots averaging 1.7 to 2.7 seconds, 6 to 9 shots per 15 seconds.
- Seedance 2.5 accepts 4 to 30 whole seconds per generation (checked against the model's input schema). How long an extension may be is not confirmed; the 60 second chain is an assumption.
- Character names are collected from speaker names and capitalised words, so check the list.

## Reference

`references/segmentation-rules.md` covers the extension and chain rules in detail, how to split mid-scene location changes, what to carry across a cut, and worked examples from the sample episode.
