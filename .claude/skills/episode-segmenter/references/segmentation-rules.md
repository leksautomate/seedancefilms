# Segmentation rules in detail

## Why these numbers

- **Up to 30 seconds per generation.** The Seedance 2.5 input schema takes `duration` as a whole number from 4 to 30, and one of the published clips was a single 20 second generation. The earlier prompts used 15 seconds plus a 15 second extension; that is still possible with `--clip 15`.
- **6 to 9 shots per 15 seconds.** Measured on five published clips (74 shots): mean shot 1.95 s, median 1.73 s.
- **3.4 spoken words per second.** Measured on 17 clean sentences from the same clips. Calm lines run 2.5 to 3.2, energetic comic lines 4 to 6.
- **Dialogue shot overhead.** A shot with spoken lines runs about a second longer than the speaking time itself (lead-in before the first word, hold after the last). The segmenter adds 0.6 s per spoken line.
- **Words per 15 seconds.** The published clips carried 16 to 26 spoken words in their first 15 seconds. About 25 is a comfortable upper bound.

Details and transcripts: `seedance-scene-prompter/references/measured-clips.md`.

## How the script estimates a scene

Every scene becomes a list of timed events.

| Event | Seconds | Notes |
|---|---|---|
| Establishing view | 2.0 | One per scene heading (`--establish`) |
| Spoken line | words / 3.4 + 0.6 | `--wps`, `--line-gap` |
| Action sentence, standalone | 2.0 | `--action`. The first sentence of an action line |
| Action line next to a spoken line | 1.0 | `--reaction`. A reaction inside the dialogue shot |
| Extra sentences in the same action line | 0.5 each | `--detail`. They describe the same shot |
| Sound cue line (`BANG!`, `CLICK.`) | 1.0 | `--sfx` |
| Pause, beat, silence, hold, stare, freeze | +0.5 each | `--pause` |
| `CUT TO`, `HARD CUT`, `FADE` | 0 | Used as a cut-point hint only |

Sanity check against the user's own prompts. The lengths of the extensions are not stated in the prompts, so
this checks the structure (how many clips a scene needs), not the exact seconds:

| Scene | Script estimate | What the user's prompts show |
|---|---|---|
| Kitchen jeans | 29.9 s, two clips | A 15 s first clip plus an extension clip |
| Restaurant phone call | 12.8 s, one clip | One 15 s clip (the dialogue-timing script gives 13.1 s) |
| Bridge chase plus exit | 27.8 s, two clips | Two prompts (7 shots and 8 shots) |

Treat the estimate as good to roughly 7 percent (an assumption, tested on one clip only: the cash-counting dialogue shot ran 3.5 s against 3.3 s estimated). That is why a segment up to 7 percent over the budget is kept and flagged `TIGHT` instead of split.

## Choosing the cut point

The script scores every possible cut inside a scene and takes the best one that leaves both pieces inside the budget.

| Situation after the cut | Score |
|---|---|
| Previous event is a spoken line | +2.0 |
| The line ends with `?`, `!` or an ellipsis | +0.5 |
| Next event is action or a transition (the exchange is finished) | +2.0 |
| Next event is the other speaker's reply (mid-exchange) | +0.5 |
| Next event is the same speaker (cut inside a speech) | -3.0 |
| Previous event is mid-motion (runs, jumps, throws, falls, crashes) | -2.0 |
| Next line is a `CUT TO` or `HARD CUT` | +1.0 |

A small bonus for a fuller first clip breaks ties. If no cut fits, the script cuts at the last event that fits and flags the segment `no clean cut point`.

## What an extension needs

The extension prompt in this project starts like this:

```
Extend the @ TAG VIDEO from the exact final frame after <CHARACTER> says: "<last line>"
Continue the same scene ... with the exact same character designs, clothing, lighting, apartment atmosphere, framing style, and emotional continuity.
```

So each `extend` segment needs from the previous one:
1. **The last spoken line**, quoted exactly (the `last_beat` field when it is dialogue).
2. **The last frame**, which should be stable: a face reacting, a held pose, a hand on an object. Avoid segments that end mid-throw or mid-fall.
3. **Positions**: who is left or right, who stands or sits, where each prop is (the training bomb on the table, the phone in a hand).
4. **Costume and prop state**: tools picked up or put down, a mask on or off, wounds, torn clothing.
5. **Lighting and time of day.**

Write these into the segment card's "Carry over" line.

## New chains (scenes over the chain length)

After one generation and one extension (60 seconds by default), the chain is full. The next segment starts a new chain.

1. Pick the last frame of the previous segment and use it as a first-frame image reference (`@Image N`, "match exactly").
2. Re-state the character and location tags, and the preserve-the-designs sentence.
3. Begin the new prompt with the beat that follows the cut, not with the cut frame.

If it is possible to end a chain at a natural scene beat (a location change, a time cut, a cliffhanger), do it. It hides the seam.

## Short scenes

| Case | Do this |
|---|---|
| Short scene, same location as the next one | Merge them. The script does this when the sum is within the clip budget. |
| Short establishing shot (city, building, sky) | Keep it short (4 to 6 s), or fold it into the first shot of the following scene. |
| Short insert (a phone buzzing, a clock) | Fold it into the neighbouring segment as one shot. |
| Short scene with a key line | Keep it as its own short clip. Request only the seconds needed. |

## Scenes that change location halfway

If a scene has no heading but the place changes (for example the chase in scene 5 ends in a different room), split it by hand into two scenes before running the script. A segment should have one location.

## Worked example: the sample episode

`examples/sample-episode.txt` has five scenes. With the defaults (30 second generations) every scene is one clip
(`examples/sample-segments.md`):

| Segment | Scene | Mode | Est. s | Request s | Note |
|---|---|---|---|---|---|
| S01 | Kitchen | single | 29.9 | 30 | 9 spoken lines, 39 words |
| S02 | Bedroom | single | 21.7 | 24 | 8 lines, 37 words |
| S03 | Underground city | single | 4.0 | 5 | Short establishing clip |
| S04 | Restaurant | single | 12.8 | 15 | |
| S05 | Bridge | single | 27.8 | 30 | The chase, the exit sphere and the teleport |

Total estimated runtime: 96 seconds in 5 clips.

With `--clip 15 --chain 30` (the earlier 15 second layout, `examples/sample-segments-15s.md`) the same episode becomes 8 clips:
the kitchen, bedroom and bridge scenes each split into a generation and an extension, with cuts after "Are you SURE? They feel so tight...",
"For what?" and "DROP THE EXIT... NOW!".
