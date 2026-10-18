# Arrogant Husband Cast Out His Loyal Wife, Only to Discover Who Signed His Paychecks — Episode 01

Production sheet. Prompts are in the scene folders and in `prompts-all.md`. Open `plan.html` for the visual plan.

## Clips in order

| Clip | Scene | Mode | Plan s | Est. s | Request s | Lines | Words | Status |
|---|---|---|---|---|---|---|---|---|
| S01a | INT. KALIO DUPLEX, PETER ODILI ROAD, PORT HARCOURT. NIGHT | generate |  | 30.8 | 30 | 4 | 60 | pending |
| S01b | INT. KALIO DUPLEX, PETER ODILI ROAD, PORT HARCOURT. NIGHT | extend |  | 18.8 | 21 | 2 | 45 | pending |
| S01c | INT. KALIO DUPLEX, PETER ODILI ROAD, PORT HARCOURT. NIGHT | new-chain |  | 23.9 | 27 | 4 | 56 | pending |
| S01d | INT. KALIO DUPLEX, PETER ODILI ROAD, PORT HARCOURT. NIGHT | extend |  | 27.7 | 30 | 5 | 51 | pending |

Estimated runtime: **101.2s** (1.7 min) in 4 clips.

Generate every clip with Seedance 2.5 at 16:9, 1080p, audio on. Each clip's brief lists its duration (whole seconds, 4 to 30) and inputs.

## Assembly notes

- Generate in the order above. An `extend` clip starts from the previous clip's exact final frame.
- When joining a generation and its extension in an editor, cut where the extension begins so no frame repeats.
- Keep one loudness target across all clips. Streaming platforms commonly normalise near -14 LUFS with true peak around -1 dBTP. Verify against the destination's current specs.
- Run `review-checklist.md` on every generated clip before it goes into the edit.
