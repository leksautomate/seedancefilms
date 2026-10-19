# Arrogant Husband Cast Out His Loyal Wife, Only to Discover Who Signed His Paychecks — Episode 01

Production sheet. Prompts are in the scene folders and in `prompts-all.md`. Open `plan.html` for the visual plan.

**Logline:** At his own promotion party, a husband publicly throws out the wife who has quietly carried him, and her calm last instruction tells the room that his pride rests on something she controls.

**Tone:** Family-friendly but cutting domestic drama: loud party cruelty on one side, held-back dignity on the other, ending on a half-laugh that has lost its confidence.

## Clips in order

| Clip | Scene | Mode | Plan s | Est. s | Request s | Lines | Words | Status |
|---|---|---|---|---|---|---|---|---|
| S01a | INT. KALIO DUPLEX, PETER ODILI ROAD, PORT HARCOURT. NIGHT | generate |  | 30.8 | 30 | 4 | 60 | ok |
| S01b | INT. KALIO DUPLEX, PETER ODILI ROAD, PORT HARCOURT. NIGHT | extend |  | 18.8 | 21 | 2 | 45 | ok |
| S01c | INT. KALIO DUPLEX, PETER ODILI ROAD, PORT HARCOURT. NIGHT | new-chain |  | 23.9 | 27 | 4 | 56 | ok |
| S01d | INT. KALIO DUPLEX, PETER ODILI ROAD, PORT HARCOURT. NIGHT | extend |  | 27.7 | 30 | 5 | 51 | ok |

Estimated runtime: **101.2s** (1.7 min) in 4 clips.

Generate every clip with Seedance 2.5 at 16:9, 1080p, audio on. Each clip's brief lists its duration (whole seconds, 4 to 30) and inputs.

## Reference images to make first

Style: **Premium cinematic 3D animated African drama, stylized semi-realistic human characters with expressive eyes, individually distinct sculpted facial features with a unique face shape, nose and jaw for every character, detailed dark and medium-brown skin tones, polished natural hair, curls and braids, emotionally exaggerated facial acting, realistic contemporary and traditional African clothing, highly detailed but uncluttered interiors and environments, warm amber and golden color palette, cinematic golden-hour or large-window lighting, soft global illumination, subtle rim lighting, moderate depth of field, realistic material textures, strong foreground character hierarchy, clear multi-character emotional staging, eye-level or cinematic three-quarter camera angles, polished animated-feature rendering, dramatic but family-friendly emotional atmosphere.**. Paste each sheet prompt into the image tool, save the result as `images/characters/<tag>.png` or `images/locations/<tag>.png`, and upload those images as references when you generate the clips. Lists to review: `characters-and-locations.md`.

| Tag | Kind | Scenes | Voice design | Status |
|---|---|---|---|---|
| `@RichardKalio` | character | 1 | yes | ok |
| `@EstherKalio` | character | 1 | yes | ok |
| `@StephanieSekibo` | character | 1 | no | ok |
| `@KalioSittingRoom` | location | 1 | | ok |

No sheet (described in full in each scene prompt): GUESTS.

## The spine

- **Act I: The party and the expulsion** (scenes 1): Show a man's arrogance, a woman's patience, and the moment she accepts being sent away in front of everyone, leaving him one sentence he cannot ignore.

## Scene notes

| Scene | Type | Mood | Build state | Why it earns its place |
|---|---|---|---|---|
| 1 | dialogue | anger | ready | The audience watches a man humiliate his wife in front of twenty guests, and the instant she leaves with her father's pen and one calm sentence, his confidence cracks: the whole series turns on that sentence. |

## Colour script

**Motif:** Gold: Richard's watch and the brass-capped pen. The watch is what he turns when he feels powerful; the pen is what Esther will not let go of. The last frame returns to the watch, stopped.

| Beat | Emotion | Dominant | Accent | Contrast | Saturation | Swatches |
|---|---|---|---|---|---|---|
| The party | smug warmth | warm amber and gold light | burgundy and fuchsia | medium | ~65% | #C98B3A #7A1F2B #C2257A |
| The expulsion | cold anger against a warm room | amber interior | sage green (Esther) against burgundy (Richard) | medium-high | ~55% | #B7792E #8A9A78 #6B1A24 |
| The door | dignity, then unease | cool rain-grey spilling into the amber room | brass of the pen and gold of the watch | high | ~45% | #4B5666 #B08A3E #D8A82A |

Hex swatches are suggestions for reference boards. Check them on a generated still before relying on them.

## Risks

- **The brass-capped pen.** A tiny prop that drifts in shape and disappears between shots Cheaper alternative: Show it large in an insert each time it matters (on the table, rolling, in her hand, in her pocket) and describe it the same way every time
- **Twenty guests in the room.** Crowds blur, duplicate faces and steal focus from the three leads Cheaper alternative: Keep guests soft in the background, a few clear silhouettes, and keep the three leads in the foreground
- **Richard's 15-second speech.** Long lip-sync can rush or drift when the request is shorter than the speech Cheaper alternative: Break it with cutaways to Esther and the guests, and request the full clip length
- **Left and right across the extensions.** Positions of Richard, Stephanie, Esther and the door can flip between clips Cheaper alternative: State the positions at the top of every clip and in each brief
- **Rain through an open door.** Rain and a door opening at the end can add unwanted weather or sound Cheaper alternative: Keep the rain visible at the windows from the start and let it blow in only in the last shots
- **Faces that look alike.** Three leads and many guests with similar features drift together Cheaper alternative: Keep each lead's face shape, nose and jaw different in the sheets and repeat the key traits in the prompt

## Unknowns (not in the script)

- Where Richard works and who actually signs his paychecks (the script leaves it as the reveal).
- Richard's, Esther's and Stephanie's hair, build and skin tone beyond what the style paragraph says.
- The layout of the sitting room: where the door, side table, chair and stage are.
- Whether Esther's bag is on the chair from the start (the script says she lifts her bag from the chair).
- What the guests wear and look like.

## Assumptions made

- English dialogue in a Nigerian English register, matching the Port Harcourt setting.
- Slow, pointed delivery at about 2.8 words per second.
- Richard and Esther are the series leads, so both get a voice design prompt.
- The title given is the movie name; this is episode 1.
- The party guests are one shared group of extras with no sheet.

## Assembly notes

- Generate in the order above. An `extend` clip starts from the previous clip's exact final frame.
- When joining a generation and its extension in an editor, cut where the extension begins so no frame repeats.
- Keep one loudness target across all clips. Streaming platforms commonly normalise near -14 LUFS with true peak around -1 dBTP. Verify against the destination's current specs.
- Run `review-checklist.md` on every generated clip before it goes into the edit.
