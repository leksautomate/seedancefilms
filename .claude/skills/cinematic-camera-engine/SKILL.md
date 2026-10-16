---
name: cinematic-camera-engine
description: Cinematic camera decision engine. Takes a scene, storyboard line, or plot beat and returns a complete camera plan - shot scale, camera movement, angle, focal length, composition, narrative function - plus an English prompt fragment ready to paste into a video prompt. Solves "I know the shot types, but which one does this scene need?". Built-in scene-to-shot decision tree covering 12 scene types x 8 emotional tones, eight classic shot-flow templates, six transition rules, a silent six-point self-check, and a color anchor for multi-shot projects. Use for camera plans, shot design, shot flow and pacing, "what shot should I use", "make the camera work less flat", or when planning the shots of a scene before writing a Seedance prompt.
version: 1.0.0-en
---

> English adaptation of `cinematic-camera-engine` by yzsp-ai (MIT License). See `ATTRIBUTION.md`.
> Sections marked **Local notes** are additions for this project and are not in the original.

# Cinematic Camera Engine

Feed it a scene description and it outputs a full camera plan: **which shot scale, how the camera moves,
what angle, which focal length, and how the shots connect.**

**Core idea:** camera language is not random. Every shot scale, movement, and angle carries emotion and
story information. This skill turns the choice into rules, so shots are matched by rule instead of by feel.

Companion skills in this project:
- `episode-segmenter` splits an episode script into clip-sized segments. Run it first.
- `seedance-scene-prompter` writes the final Seedance prompt from this skill's shot plan and checks dialogue timing.
- `references/camera-angles.md` in `seedance-scene-prompter` is the plain-language angle glossary.

---

## Iron rules (read before choosing shots)

1. **Shot scale must match the narrative job.** Show the environment: wide. Show a relationship: medium. Deliver emotion: close. Reversing this means the audience cannot read the information.
2. **Adjacent shots must differ by at least 2 scale levels.** Medium to medium reads as a jump cut. Medium to medium close-up (1 level) is barely different. Medium to extreme close-up (2 levels) cuts cleanly. AI models are insensitive to small scale differences, so a 2-level jump is needed for a visible change.
3. **Every camera move needs a story reason.** Push in = focus attention. Pull out = reveal the environment or loneliness. Slide sideways = follow or scan. A move with no reason is just shake.
4. **Camera angle signals power.** Low angle = the subject is strong and imposing. High angle = the subject is small and vulnerable. Eye level = equal and objective. An angle that contradicts the story makes the audience uneasy.
5. **One shot does one job.** Either show space, or deliver emotion, or show an action. Three jobs in one shot and the model does all three badly.
6. **Camera speed matches emotional rhythm.** Tension: fast moves or handheld shake. Calm: slow drift or locked-off. A speed/mood mismatch feels "off" even when viewers cannot say why.

## Anti-patterns

| Anti-pattern | Why it fails | Do this instead |
|---|---|---|
| Everything in medium shot | No hierarchy of importance | Assign scale by information level: environment wide, relationship medium, emotion close |
| 3 or more identical scales in a row | Visual fatigue; the model generates near-identical frames | At most 2 in a row; the third must jump scale |
| Writing just "push in" | No start or end point, so the model moves randomly | `Slow dolly in from medium shot to close-up, ending on the character's eyes` |
| All dialogue as shot/reverse-shot | Mechanical | Mix in over-the-shoulder, two-shots, and reaction close-ups |
| Static camera for an intense scene | Frozen picture vs. violent story | Handheld or Steadicam with speed changes |
| Every shot has a move | Eye fatigue; movement becomes noise | Move:static about 3:7 (everyday), 5:5 (action), 7:3 (chase) |
| "Close-up" without saying of what | The model picks a random subject | `Extreme close-up on trembling fingers gripping the letter` |

---

## STEP 0: Scene analysis, automatic camera plan (the decision engine)

When you receive a scene, storyboard, or plot description, run this tree:

```
Input: scene description / storyboard script / mood keywords
  |
  |- Extract 4 elements:
  |    1. Scene type (dialogue / action / inner monologue / environment / transition / ensemble ...)
  |    2. Emotional tone (calm / tense / warm / sad / awe / fear / joy / anger)
  |    3. Action intensity (static / light / medium / intense)
  |    4. Number of characters (0 / 1 / 2 / group)
  |
  |- Look up:
  |    -> references/scene-camera-recipes.md  (12 scene types x full camera plans)
  |    -> references/shot-flow-patterns.md    (multi-shot sequence templates)
  |
  |- Output the full camera plan:
  |    shot scale + movement + angle + focal length + composition notes
  |
  |- Fallback (not enough information):
       default = medium shot + locked-off camera + eye level + 50mm + rule of thirds
       Say: "Used the default neutral camera plan. Give the scene's mood to adjust it."
```

### Quick scene-type lookup

| Scene keywords | Scene type | Default starting scale |
|---|---|---|
| talk / chat / argue / confess / interrogate | Dialogue | Two-shot medium, then shot/reverse-shot |
| fight / chase / escape / explosion | Action | Wide to establish, then medium-close action |
| monologue / memory / thinking / staring | Inner monologue | Close-up / extreme close-up |
| walks in / arrives / enters / comes to | Character entrance | Wide, medium, close (progressive reveal) |
| city / mountain / ocean / building / space | Environment | Extreme wide / wide |
| first appearance / debut / introduced | Character introduction | Full shot to establish, medium to place, close-up on the memorable detail |
| parting / leaving / ending / death | Farewell / ending | Close-up, then pull out to wide |
| discovers / reveals / truth / shock | Revelation | Close-up reaction, then pull out to reveal the whole |
| waiting / lonely / bored / empty | Static emotion | Wide (person small in the space) |
| celebration / cheering / victory / reunion | Ensemble climax | Medium to full shot (everyone in frame) |
| transition / time passing / montage | Transition | Mixed scales, fast cuts |
| fear / stalking / spying / danger | Suspense / horror | POV + Dutch angle + handheld |

---

## STEP 1: Choose the shot scale

Full tables in `references/camera-decision-tables.md` (STEP 1): the seven scales with narrative function,
and mood to scale tendencies.

- Emotional or inner scenes: close-up to extreme close-up
- Action or interaction: medium to full shot
- Environment or epic: wide to extreme wide
- Character entrance: wide, medium, close (progressive reveal)

## STEP 2: Choose the camera movement

Full tables in `references/camera-decision-tables.md` (STEP 2): 11 movements mapped to mood, and action
intensity to movement mix.

- Static scenes: 80% locked-off + 20% slow push
- Intense scenes: 80% moving (handheld, whip pan, fast push/pull) + 20% locked-off

## STEP 3: Camera angle and focal length

Full tables in `references/camera-decision-tables.md` (STEP 3): 7 angles mapped to power and mood, 5 focal
length bands, and a composition quick-pick.

- Eye level = equal, low angle = authority, high angle = small, Dutch angle = unease
- Wide lens = space, standard = objective and real, telephoto = voyeuristic compression

## STEP 4: Shot flow, connections and rhythm

Shots do not exist alone. How a group of shots connects sets the pace of the story.

### Classic sequence templates

| Template | Shot flow | Use for |
|---|---|---|
| Progressive reveal | wide, full, medium, close-up | Character entrance, setting the scene |
| Emotional focus | medium, medium close-up, close-up, extreme close-up | Emotion building step by step |
| Shocking reveal | close-up (reaction), fast pull out to wide | Revealing the truth or a scale |
| Standard dialogue | two-shot medium, shot/reverse-shot (medium close-ups), reaction close-up | Ordinary conversation |
| Escalating dialogue | medium, close-up, extreme close-up (scale tightens as conflict rises) | Arguments, interrogations |
| Action sequence | wide (establish), medium (action), close-up (impact), wide (result) | Fights, chases |
| Loneliness / departure | close-up (emotion), slow pull out to wide (person shrinks in the space) | Goodbyes, loss |
| Ensemble climax | close-up cuts of each character, then a wide of everyone | Team assembling, celebration |

### Transition rules

| Rule | Reason | If broken |
|---|---|---|
| Adjacent shots differ by 2 or more scale levels | A 1-level jump gives the AI model too little difference | The audience feels a "jump" |
| Consistent movement direction | Two consecutive shots must not move 180 degrees opposite | Audience loses spatial sense |
| Do not cross the axis | Keep a two-person dialogue shot from the same side | Audience cannot tell who is where |
| Locked-off shot followed by a moving shot | All static is dull; all moving is dizzying | The rhythm loses its breath |
| A long shot after a fast-cut run | Continuous fast cuts tire the eye | Needs a landing point to breathe |

Full sequence templates and variants: `references/shot-flow-patterns.md`.
Full scene to camera recipes: `references/scene-camera-recipes.md`.

---

## STEP 5: Output format

### Single-shot plan
```
[Scale]     level - English term
[Movement]  type - start -> end, speed, duration
[Angle]     type - degrees
[Lens]      range - spatial effect
[Framing]   rule - subject position
[Function]  what this shot delivers (information / emotion)
[Prompt]    English fragment ready to paste into a prompt
```

### Multi-shot plan
```
Shot group: [scene name]
Emotional arc: [start emotion] -> [end emotion]

Shot 1: [scale] + [movement] + [angle] - [narrative function]
Shot 2: [scale] + [movement] + [angle] - [narrative function]
Shot 3: [scale] + [movement] + [angle] - [narrative function]
...
Connection logic: [why the shots are ordered this way]
```

Prompt fragments are always in English. Explanations follow the user's language.

---

## STEP 6: Self-check (silent, not shown to the user)

After building the plan, check these six points silently:

1. Do adjacent shots differ by 2 or more scale levels?
2. Does every camera move have a story reason (not movement for its own sake)?
3. Does each camera angle match the power relationship?
4. Does each shot do only one job?
5. Does camera speed match the emotional rhythm?
6. Are there 3 or more identical scales in a row?

If any fail, fix the plan first and then output it. Do not report the checking.

---

## STEP 7: Cross-shot color consistency

In multi-shot projects, **color drift** is the most common visual break: shots of the same scene have
different color temperature, saturation, or tone, and look wrong when edited together.

### Rules

1. **Name a color reference shot.** In a multi-shot sequence the first approved shot becomes the sequence's color anchor. Later shots must follow its tone.
2. **Describe color in numbers.** Not "cool tones" but specific parameters: `desaturated ~40%, teal-grey dominant, Kodak Vision3 500T`.
3. **Lock the project palette.** At the start, decide the project-wide color system (temperature, saturation range, dominant colors) and write it into the project's "medium style lock" paragraph. Every shot's prompt fragment must include that lock sentence.
4. **Color changes need a story reason.** Cold to warm marks an emotional turning point. An unexplained color jump is a bug.

### Lesson learned

40 shots generated independently: some warm yellow, some cold blue, some normal saturation. Cut together,
the color jumps around. Fixing the grade afterward means re-editing every image. Locking it up front is cheaper.

### Color anchor prompt template

```
Color grade anchor: [color description taken from the approved anchor shot]
Example: "Desaturated cold teal-grey palette ~40% saturation,
Kodak Vision3 500T pushed 1 stop, silver-retention/bleach-bypass,
heavy 35mm grain. Skin tones shifted olive-grey."
```

Paste this template at the start of each shot plan's prompt fragment.

---

## Local notes for this project (not in the original)

These adapt the engine to the Seedance workflow used in `seedance-scene-prompter`.

1. **House-style prompts forbid camera moves.** The Seedance prompts in this project say "Use ONLY hard cuts. NO tracking shots, camera slides, whip pans, or continuous camera transitions." When that header is present, ignore the movement column of any recipe and use locked-off framing plus hard cuts. Express "push in" as a cut to a tighter scale instead. Use real camera movement only when the user asks for it (for example a chase scene in compact style).
2. **Shot lengths run shorter than the original's AI guidance.** Measured on five published clips: the average shot is 1.7 to 2.7 seconds (median 1.7). For dialogue comedy use the "fast" variants in the shot-flow templates and give each spoken line its own shot. See `seedance-scene-prompter/references/measured-clips.md`.
3. **Every clip has a budget.** A Seedance generation is 15 seconds (extendable by another 15). Plan shots so the summed shot times fit the segment's budget from `episode-segmenter`. A 15 second clip holds about 6 to 9 shots.
4. **Scale-jump rule for dialogue exchanges.** Two speakers in alternating close-ups both sit at close-up scale, which breaks rule 2 by design. Alternate a medium reaction or a two-shot between close-ups every 3 to 4 shots, as the dialogue template says.
5. **Hand-off.** Give each shot a heading in the form `SHOT N - <SCALE> - <ANGLE>` so `seedance-scene-prompter` can reuse it directly, and keep the lens and framing words in the framing sentence.
