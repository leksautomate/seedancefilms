# Patterns found across the example prompts

Source: the eight prompts in `../examples/` (two kitchen comedy clips, a bedroom comedy scene, two
restaurant clips, a 20s fragment, and two chase/escape sequences), plus the camera-angle video.

## Two prompt styles

**Full style** (examples 01-05): a header block, voice blocks, then long shot descriptions with a
`HARD CUT.` after each. Used for dialogue-heavy comedy where acting detail and voice matter.

**Compact style** (examples 07-08, 06): short shot lines separated by `CUT TO:`, little or no header.
Used for fast action where framing and continuity matter more than acting. Image references
(`@Image 7`) carry the look; one trailing IMPORTANT block locks the fragile details.

## What every prompt does

| Element | Where it appears | Why it is there |
|---|---|---|
| `@TAG` / `@Image N` references | Header and shots | Binds uploaded character, location, prop, and framing images |
| "Preserve the exact ... designs, proportions, clothing" | Header (01, 03, 04, 05) | Stops the model redesigning characters between shots and clips |
| Hard cuts only, no tracking/whip pans | Header of every full-style prompt | Seedance handles cuts reliably; camera moves drift |
| `NO music` plus an allowed-sounds list | Header or last IMPORTANT block | Keeps the mix clean and dialogue clear |
| Per-character voice block | 01, 03 | Locks accent, pitch, tone, delivery |
| "SAME voice" in every dialogue shot | 01, 02 | Keeps voices consistent across shots and across extension clips |
| One idea per shot | All | Short shots, clear cut points |
| Reaction shots between lines | 01, 03 | Alternating speaker close-ups give the comedic rhythm |
| Cropping instructions | 01 shot 1, 06 | Directs attention (hands, muzzle, chest, no eyes) |
| Exclusions ("Do NOT show", "No dialogue", "NEVER reveals") | 05, 08 | Prevents the model filling a gap with the wrong thing |
| IMPORTANT locks on fragile attributes | 03 (nose through mask), 07 (drone size) | Repeats what the model tends to get wrong |
| Explicit ending | All | `END HERE`, `CUT TO BLACK`, or a sound-only payoff |

## Dialogue habits

- Lines are short, conversational, and built for a punchline: "Do I look fat in these jeans?" / "No." / "Are you SURE?! They feel so tight..." / "Then get a bigger size."
- The speakers alternate, one line per shot, and the cut lands right after the line.
- Capital letters mark stress (`SURE`, `TEN`, `THEY'RE ALREADY A SIX!`).
- Ellipses and dashes mark delivery (`Here we go...`, `You thought—` / `...what?`).
- A line can be split across two shots when a character builds up (example 02).
- Delivery notes name the emotion plus the physical manner: "breathless", "dry and baffled", "low, dangerous, not screaming yet".
- A silent shot is stated: "No dialogue."

## Comedy engine (examples 01-03)

A serious, absorbed character is interrupted by a trivial, ridiculous question. The calm character answers
in a flat deadpan. The interrupter escalates. The final line flips the logic ("Six?! I thought you were, like, a TEN!"),
and the last shot is a resigned reaction ("Here we go...") followed by a cut to black.

## Cliffhanger engine (example 05)

Quiet routine (closing the shop), a small sweet beat (the kitten), a reaction that signals danger (kitten
freezes, ears back), the character looks up at something the camera never shows, hard cut to black, one sound
(pig squeal) gives the payoff.

## Chase / escape engine (examples 07-08)

Short shots with LEFT/RIGHT positions kept constant, a POV shot for the threat, an insert shot of the key
prop being activated, a one-line quiet beat after the escape ("Almost."), cut to black. Size and
behaviour locks are repeated in a closing IMPORTANT block.

## Clip lengths seen

- 15s generation: 7 shots (01, 04), 8 shots (05 extension).
- 15s extension: 6 shots (02), 8 shots (05).
- 20s generation: fragment in example 06 (shots separated by `========================`).
- Longer scenes (03, 10 shots / 37 spoken words) estimate above 15s, so they need either a longer generation or two clips.
