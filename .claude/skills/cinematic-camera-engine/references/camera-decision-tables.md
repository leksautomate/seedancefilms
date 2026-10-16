# Camera Decision Tables

> English adaptation of `camera-decision-tables.md` from cinematic-camera-engine by yzsp-ai (MIT). See `../ATTRIBUTION.md`.
> Extracted from SKILL.md STEP 1-3 for on-demand loading: shot scale, camera movement, angle and focal length.

---

## STEP 1: Shot scale

### The seven scales and their narrative function

| Scale | Term | Frame range | Narrative function | Emotional effect | Prompt keywords |
|---|---|---|---|---|---|
| Extreme wide | Extreme Wide Shot | Tiny figure, environment fills the frame | Establish the world, epic feel | Small, vast, lonely | `extreme wide shot, tiny figure in vast landscape` |
| Wide | Wide Shot | Full body plus lots of environment | Establish place and spatial relationships | Objective, calm | `wide shot, full body with surrounding environment` |
| Full | Full Shot | Whole body | Body language, costume | Neutral, introductory | `full shot, character from head to toe` |
| Medium | Medium Shot | Waist up | Dialogue, interaction, action | Natural, close but with distance | `medium shot, waist up` |
| Medium close-up | Medium Close-up | Chest up | Expression plus some gesture | Growing intimacy | `medium close-up, chest and above` |
| Close-up | Close-up | Head and shoulders | Emotion, inner life | Strong emotional projection | `close-up on face` |
| Extreme close-up | Extreme Close-up | A part (eye, hand, object) | Extreme emphasis, detail reveal | Tension, focus, peering | `extreme close-up on [specific part]` |

### Mood to scale tendency

| Mood | Preferred scale | Why |
|---|---|---|
| Calm / everyday | Medium to medium close-up | Natural conversation distance |
| Tense / suspense | Close-up to extreme close-up, occasional wide | Close reads the face, wide isolates the character |
| Awe / epic | Extreme wide to full | Show scale |
| Sad / despair | Close-up (emotion) plus wide (loneliness) | Alternating works best |
| Warm / intimate | Medium close-up to close-up | Near but not invasive |
| Anger / outburst | Medium, then fast push to close-up | From controlled to out of control |
| Fear | Extreme close-up (reaction) plus wide (threat source) | Alternate subjective and objective |

---

## STEP 2: Camera movement

### Movement x mood

| Movement | Term | Emotional effect | Use for | Speed reference |
|---|---|---|---|---|
| Slow push | Slow Dolly In | Guides focus, gradual reveal | Discovering the truth mid-dialogue, resolve | 3-5s to reach the target |
| Fast push | Crash Zoom / Fast Push | Shock, discovery, emphasis | Key reveal, twist | 0.5-1s |
| Slow pull | Slow Pull Out | Reveal the whole, loneliness, parting | Endings, goodbyes, despair | 3-8s |
| Fast pull | Fast Pull Out | Shocking reveal, scale | An army appears, disaster scale | 0.5-1.5s |
| Slide | Dolly/Track Left/Right | Follow, scan, parallel story | Following a walk, showing a space | Match the character's speed |
| Orbit | Arc Shot / Orbit | Drama, ceremony, scrutiny | Hero moment, standoff, oath | 2-5s for a half circle |
| Crane | Crane Up/Down | Power shift, reveal, overview | Elevating a figure, then revealing truth; city overview | 2-4s |
| Handheld | Handheld | Documentary feel, tension, chaos | Chase, fight, panic | Irregular |
| Locked-off | Static / Locked | Objective, calm, oppressive (long take) | Everyday dialogue, interrogation, waiting | n/a |
| Whip pan | Whip Pan | Sudden shift of attention | Quick switch between characters, scares | 0.2-0.5s |
| Dolly zoom | Dolly Zoom / Vertigo | Warped space, psychological imbalance | A character's perception collapsing, fear | 2-3s |

### Action intensity x movement mix

| Action intensity | Recommended movement | Moving share | Speed |
|---|---|---|---|
| Static (dialogue / waiting) | Locked-off plus an occasional slow push | 20% moving, 80% locked | Very slow |
| Light (walking / everyday) | Slow push / slow pull / side-follow | 40% moving, 60% locked | Slow to medium |
| Medium (argument / running) | Handheld + slide + fast push | 60% moving, 40% locked | Medium to fast |
| Intense (fight / chase) | Handheld + whip pan + fast push and pull | 80% moving, 20% locked | Fast with speed changes |

---

## STEP 3: Camera angle and focal length

### Angle x power / mood

| Angle | Term | Power signal | Emotional effect | Prompt fragment |
|---|---|---|---|---|
| Eye level | Eye Level | Equal | Objective, neutral, empathy | `eye-level camera angle` |
| Slight low | Slight Low Angle | Mild admiration | Likeable, trust | `slightly low camera angle, looking up 10 degrees` |
| Low angle | Low Angle | Subject is strong | Imposing, heroic, oppressive | `low angle shot, looking up at character, imposing` |
| Slight high | Slight High Angle | Mild weakness | Vulnerable, cute, sympathetic | `slightly high angle, looking down 10 degrees` |
| High angle | High Angle | Subject is small | Vulnerable, trapped, despairing | `high angle shot, looking down, character appears small` |
| Bird's eye | Bird's Eye / Top-down | God's-eye view | Omniscient, fated, detached | `bird's eye view, directly overhead` |
| Dutch angle | Dutch Angle | Imbalance | Uneasy, mad, chaotic | `Dutch angle, tilted horizon 15-30 degrees` |

### Focal length x sense of space

| Focal length | Spatial effect | Emotional effect | Use for | Prompt fragment |
|---|---|---|---|---|
| 14-24mm ultra wide | Exaggerated, stretched space | Grand, distorted, oppressive | Epic wides, claustrophobic fear | `ultra wide-angle 16mm lens, exaggerated perspective` |
| 24-35mm wide | Open, natural space | Open, documentary, everyday | Establishing the environment, documentary look | `wide-angle 28mm lens, natural spatial depth` |
| 35-50mm standard | Close to human vision | Objective, real, balanced | General storytelling, dialogue | `standard 50mm lens, natural perspective` |
| 85-135mm medium tele | Compressed space, blurred background | Intimate, isolated, focused | Portraits, emotional close-ups | `85mm telephoto, shallow depth of field, background blur` |
| 200mm+ tele | Extreme compression, peeping feel | Voyeuristic, surveillance, distance | Stalking, hidden-camera view | `200mm telephoto, compressed perspective, voyeuristic` |

### Composition quick-pick

| Rule | Use for | Prompt fragment |
|---|---|---|
| Rule of thirds | General default, subject on a third line | `rule of thirds composition, subject on the left third` |
| Centered | Symmetry, ceremony, hero monologue, boss entrance | `centered composition, symmetrical framing` |
| Diagonal | Dynamic feel, guiding action direction | `diagonal composition, dynamic leading lines` |
| Foreground framing | Peeping, layered depth, suspense | `foreground framing, shooting through [obstacle]` |
| Negative space | Loneliness, smallness, pressure, minimalism | `negative space composition, vast empty area around subject` |
