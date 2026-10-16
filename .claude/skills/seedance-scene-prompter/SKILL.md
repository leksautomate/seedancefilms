---
name: seedance-scene-prompter
description: Writes shot-by-shot Seedance 2.5 prompts for fast, cinematic adult animated scenes (dialogue comedy, chases, cliffhangers) in the established house style, and checks that the spoken dialogue fits the clip length. Use when the user asks for a Seedance prompt, a scene or extension prompt, a "first 15 seconds" or "extend" prompt, shot lists with @TAG character/location references, or asks how many seconds a scene's dialogue will take.
---

# Seedance Scene Prompter

Turns a scene idea (or a rough script) into a Seedance 2.5 prompt that follows the
structure of the prompts in `examples/`, then counts the spoken English words and
estimates whether the scene fits the clip length.

Read these when needed:
- `references/prompt-patterns.md` - the patterns found across the example prompts
- `references/measured-clips.md` - transcripts and measured speaking rate, shot length, and words per 15 seconds from five published clips
- `references/camera-angles.md` - the 8 core camera angles plus extra terms, and how to name them in a prompt
- `examples/` - eight real prompts (generation, extension, no-dialogue action, 20s fragment)
- `scripts/dialogue_timing.py` - dialogue word count and running-time estimate

## Where this fits in the pipeline

Working from a whole episode? Run the other skills first (see `docs/agent-pipeline.md`):

1. `episode-segmenter` splits the script into segments (clips of up to 30 s, extensions, new chains). Each segment arrives with its characters, estimated seconds, last spoken line and mode (`single`, `generate`, `extend`, `new-chain`).
2. `cinematic-camera-engine` turns the segment's scene type and mood into a shot plan (`SHOT N - SCALE - ANGLE`). When this skill's header says hard cuts only, use its scales and angles and ignore camera movement.
3. This skill writes the prompt from that plan. For `extend` and `new-chain` segments use the extension style below and quote the last spoken line of the previous segment.
4. Run the timing check in section 4 on every finished prompt.

If the user hands over a single scene or an idea instead, skip steps 1 and 2 and start at section 1.

## 1. Collect the inputs

Ask only for what is missing. Do not ask for anything the user already gave.

| Input | Default if the user does not say |
|---|---|
| Clip length (per generation) | The scene's own length, 4 to 30 seconds (Seedance 2.5 renders up to 30 in one generation) |
| New scene or extension of an existing clip | New scene |
| Characters and their `@TAG` names | Use the names given, write them as `@ TAG NAME` |
| Locations/props with `@TAG` names | Same |
| Reference images (`@Image N`) and whether each is "match exactly" or "DESIGN ONLY" | None |
| Tone | Fast, sharp, cinematic, comedic |
| Dialogue (draft lines or just the beats) | Draft it from the beats |
| Voice description per speaking character | Reuse an existing voice block if the character has one |

Keep the user's tag spelling exactly (`@ TAG GIRL`, `@TAG ROXIE`, `@Image 4`). The tags are
how the user's reference uploads are bound to the prompt.

## 2. Plan the shots first

1. One idea per shot. Each shot gets one framing, one action, at most one or two spoken lines.
2. Pick a camera angle for each shot from `references/camera-angles.md`. Vary the angles; do not repeat the same one more than twice in a row.
3. Comedy and tension both run on a setup, escalation, punchline rhythm. Put the punchline line on the shot right before a cut, or on the last shot.
4. Plan the ending: `CUT TO BLACK`, `END HERE`, or a cliffhanger where the camera never reveals the threat and only a sound pays it off (see example 05).
5. Budget the time (see section 4) before writing the full prompt.

## 3. Write the prompt

Use this order. Sections in brackets are optional.

```
Create [the first 15 seconds of] a [fast-paced] cinematic adult animated scene.      (use the clip's own length: 4 to 30 seconds)
(Extension: "@ TAG VIDEO extend the video by another 15 seconds. Start exactly after <last event>."
 or "Extend the @ TAG VIDEO from the exact final frame after <CHARACTER> says: “<last line>”")

<One short paragraph per character: where they are, what they are doing. Use @ TAG names.>

Preserve the exact established designs, proportions, clothing, <location @ TAG>, lighting,
colors, and visual style for <CHARACTER @ TAG> and <CHARACTER @ TAG>.

IMPORTANT:
Use ONLY hard cuts between shots.
NO tracking shots, camera slides, whip pans, or continuous camera transitions.
Keep the pacing fast, sharp, cinematic, and comedic.
[The comedy comes from ...]            <- one sentence stating the engine of the scene
NO music. Only <the exact list of allowed sounds>.

[<NAME>'S VOICE:  pitch, tone, articulation, rhythm, delivery. One block per speaking character.]

SHOT 1 — <SHOT TYPE> — <ANGLE / POSITION>
<framing sentence: where the camera is, what is in frame, what is cropped out>
<action in present tense, in the order it happens>
[<NAME>, <delivery>:
“<line>”]
HARD CUT.

SHOT 2 — ...

END HERE.   (or: CUT TO BLACK. / IMMEDIATE CUT TO BLACK.)
```

Rules that carry through every example:

- **Header lines are fixed.** Always include the hard-cuts-only rule, the no-tracking/whip-pan rule, and the music rule. Name the allowed sounds explicitly (room ambience, footsteps, ringing phone, and so on).
- **Voices are described once, then referenced.** In every dialogue shot write "In her SAME <accent> voice" or "in his SAME deep, gravelly, deadpan voice". Never redefine the voice mid-prompt.
- **Dialogue format:** `NAME, how it is said:` on its own line, then the line in curly quotes on the next line. Keep delivery notes short and physical ("breathless", "dry and baffled").
- **Short lines.** Aim for 8 words or fewer per line. Split anything longer across two shots or cut it. A line split across shots is allowed (example 02: "You thought—" on a wide shot, "...what?" on the next).
- **Shot headings** use `SHOT N — TYPE — ANGLE` in capitals. Every shot ends with `HARD CUT.` (or `CUT TO:` in the compact style of examples 07 and 08). Use one style per prompt.
- **Stage reactions.** Write expression changes as steps ("confusion → disbelief → outrage") and physical beats (shoulders jerk, eyes widen, hands twitch).
- **Cropping and exclusions are stated outright.** "Only the lower part of WOLF's muzzle, his chest, and his hands are visible." "Do NOT show Roxie." "No dialogue." "The camera NEVER reveals what it is."
- **Lock fragile details with IMPORTANT.** If the model tends to drift (a drone that must stay 35-45 cm, a nose that must stay visible through a mask, left/right positions), state it in the shot and repeat it in a closing IMPORTANT block.
- **Image references:** `matching @Image 7` means copy the framing; `@Image 4 is DESIGN ONLY` means use the look but not the pose or size.
- **Left/right positions** are spelled out when characters move together ("Roxie LEFT, Diesel RIGHT").
- **Sound cues** are written as words in caps on their own line (`RING. RING.`, `CLANK.`, `BANG! BANG! BANG!`). They are not dialogue.
- **Extensions** restate that the designs, clothing, lighting, and atmosphere must match, start from the exact final frame, and quote the last spoken line so the first new shot continues from it.

## 4. Check the dialogue and the timing

Always run this after drafting. Save the prompt to a text file, then:

```
python3 -I .claude/skills/seedance-scene-prompter/scripts/dialogue_timing.py prompt.txt --max 15
```

Flags: `--max` clip limit in seconds, `--wps` spoken words per second (default 3.4, measured on
published clips; use 2.5 to 3.0 for slow deadpan or dramatic delivery, 4.0 for frantic comedy), `--json` for machine-readable output.

The script splits the prompt on `SHOT N`, counts the words inside quotation marks per shot, adds pauses
and a minimum visible time per shot, and prints a table with lines, words, speaking seconds, shot seconds, and a
verdict (FITS, TIGHT, TOO LONG). It skips quotes that only describe an expression, repeat the previous clip's
last line, or point back to a line already counted.

Report the table to the user in the reply: dialogue lines, dialogue words, estimated speaking seconds,
estimated total seconds, and the verdict against the clip length.

Rules of thumb taken from the example prompts (they are estimates, not guarantees):

- Example 01 shipped 7 shots, 6 lines and 25 spoken words inside a 15 second generation (script estimate: 12.5s).
- Measured on five published clips (transcribed with word timestamps, see `references/measured-clips.md`): speech runs 3.4 words per second pooled (median 4.0); calm or deadpan lines run 2.5 to 3.2, energetic comic lines 4 to 6.
- Spoken words in the first 15 seconds of the published clips: 16 to 26. Keep a 15 second clip to about 25 spoken words or fewer, and a 30 second clip to about 50.
- 74 shots measured: the average shot lasts 1.7 to 2.7 seconds (median 1.7), so plan for 6 to 9 shots per 15 seconds (12 to 18 in a 30 second clip).
- A dialogue shot with a reaction or action beat runs about 1 second longer than its speaking time (cash clip: 7 words, 3.5 second shot). The script estimate is the tight minimum, so leave about 0.5 seconds of slack per dialogue shot.
- Shots with no dialogue still need about 1.2 to 2 seconds each.
- If the estimate is TOO LONG: trim lines first, then merge or drop a visual-only shot, then split into a first clip plus an extension prompt.
- If the estimate is TIGHT: trim one line or one beat so the model does not rush the delivery.

State the assumptions used (words per second, clip limit) so the user can correct them. If the user reports
that a real generation ran faster or slower than the estimate, rerun with an adjusted `--wps`.

## 5. Final checklist before replying

- [ ] Header has: scene summary, @ TAG characters and locations, preserve-designs sentence
- [ ] IMPORTANT block has hard cuts only, no tracking/whip pans, pacing, music rule, allowed sounds
- [ ] Every speaking character has a voice block and every dialogue shot says "SAME voice"
- [ ] Every shot has a type, an angle, framing, action, and a closing cut
- [ ] No shot carries more than two spoken lines; no line over about 8 words
- [ ] Fragile details are locked with IMPORTANT or "NEVER"/"Do NOT"
- [ ] Ending is explicit (cut to black, END HERE, or sound-only payoff)
- [ ] Timing script was run and its result is reported
- [ ] Extension prompts start from the exact last frame and quote the last line

## 6. Output format

Give the user: (1) the finished prompt in one code block, ready to paste, (2) the timing table and verdict,
(3) one or two lines listing any assumptions or trims made. Do not add commentary inside the prompt block.
