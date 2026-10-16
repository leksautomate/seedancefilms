# Ain Jalut - The Spring of Goliath — Episode 02 — The Slave Who Would Rule

Production sheet. Prompts are in the scene folders and in `prompts-all.md`. Open `plan.html` for the visual plan.

**Logline:** A former slave who swore to protect a dead sultan's son takes the boy's throne because Egypt must have a sword before the Mongols arrive.

**Tone:** Serious, slow-burn historical drama; low voices, held silences.

## Clips in order

| Clip | Scene | Mode | Plan s | Est. s | Request s | Lines | Words | Status |
|---|---|---|---|---|---|---|---|---|
| S00 | Hook | single | 18 | 22.8 | 26 | 4 | 36 | ok |
| S01 | The Market | single | 33 | 31.9 | 30 | 7 | 53 | ok |
| S02a | The Dead Sultan | generate | 40 | 20.1 | 23 | 3 | 32 | ok |
| S02b | The Dead Sultan | extend |  | 20.2 | 23 | 4 | 42 | ok |
| S03a | The Boy On The Throne | generate | 55 | 30.7 | 30 | 6 | 54 | ok |
| S03b | The Boy On The Throne | extend |  | 25.9 | 29 | 6 | 52 | ok |
| S04 | The Wall At Night | single | 30 | 31.7 | 30 | 6 | 54 | ok |

Estimated runtime: **183.3s** (3.1 min) in 7 clips.

Generate every clip with Seedance 2.5 at 16:9, 1080p, audio on. Each clip's brief lists its duration (whole seconds, 4 to 30) and inputs.

## Reference images to make first

Style: **2D anime**. Paste each sheet prompt into the image tool, save the result as `images/characters/<tag>.png` or `images/locations/<tag>.png`, and upload those images as references when you generate the clips. Lists to review: `characters-and-locations.md`.

| Tag | Kind | Scenes | Voice design | Status |
|---|---|---|---|---|
| `@Qutuz` | character | 0, 2, 3, 4 | yes | ok |
| `@QutuzChild` | character | 1 | no | ok |
| `@ShajarAlDurr` | character | 2 | no | ok |
| `@SultanAlMansurAli` | character | 3 | no | ok |
| `@SultanAybak` | character | 2 | no | ok |
| `@ElderEmir` | character | 0, 3, 4 | yes | ok |
| `@Rider` | character | 3, 4 | yes | ok |
| `@QutuzTent` | location | 0 | | ok |
| `@DamascusSlaveMarket` | location | 1 | | ok |
| `@CairoCitadelRoyalBathChamber` | location | 2 | | ok |
| `@CitadelThroneRoom` | location | 3 | | ok |
| `@CitadelWall` | location | 4 | | ok |

No sheet (described in full in each scene prompt): DEALER, BUYER.

## Not generated (edit room)

- Opening: [0:00-0:04] DREAMINA ORIGINALS OPENING
- Scene 0 on-screen text: Damascus. Many years earlier.
- Scene 2 on-screen text: Cairo Citadel, 1257.
- End card: END CARD [2:56-3:00] TEXT: Episode 03: The Exile | #dreaminaoriginals

Runtime plan: 180s in all, so 172s of generated video once the 4s opening and the 4s end card are taken out. Estimated generated video: 183s in 7 clips.

## Production notes (from the script)

- Debated history: Qutuz's royal-origin claim (Mahmud, nephew of Khwarazm-Shah) comes from later tradition. The scene frames it as the boy's own claim, which the dealer ignores.
- Aybak's death (1257): sources attribute it to Shajar al-Durr's orders. Shown as an aftermath scene only.
- Ali's removal: Qutuz took the throne in late 1259 citing the Mongol threat. Ali's later fate is kept off screen.
- Signature clip shot: the boy's chain closing, cut to the adult's eyes.

## The spine

- **Act I: The claim and the wound** (scenes 0, 1): State the accusation, then show where the man comes from.
- **Act II: The oath and the theft** (scenes 2, 3): He swears to protect the boy, then takes the throne from him.
- **Act III: The clock starts** (scenes 4): The theft becomes a purpose, and the Mongols reach Aleppo.

## Scene notes

| Scene | Type | Mood | Build state | Why it earns its place |
|---|---|---|---|---|
| 0 | dialogue | tense | ready | It states the episode's argument in four lines, a slave on a throne and a boy who cannot lift a sword, before the market shows where the man comes from. |
| 1 | dialogue | sad | ready | It turns the throne into a promise made at ten: a boy who will not cry decides to build a home no one can sell. |
| 2 | dialogue | tense | ready | It ties the oath to its cause: Qutuz swears to protect Aybak's son, the debt he breaks in the next scene. |
| 3 | dialogue | tense | ready | It is the turn of the episode: the protector removes the boy he swore to keep alive, and calls it keeping him safe. |
| 4 | dialogue | tense | ready | It turns the theft into a purpose, 'a reason to be remembered', and starts the clock the next episode runs on. |

## Colour script

**Motif:** Red: Qutuz's coat in the tent, the red-gold coat of the dead sultan, and the red coat again on the dark wall. It tracks the throne from one man to the other.

| Beat | Emotion | Dominant | Accent | Contrast | Saturation | Swatches |
|---|---|---|---|---|---|---|
| Act I | pressure, then loss | torch amber and dust ochre | deep red (Qutuz's coat) | high in the tent, medium in the market | ~55% | #d9822b #b58a4e #7a1f1f |
| Act II | grief, then cold resolve | pale marble and steam, then low gold | red-gold (Aybak's coat) | medium | ~45% | #d8d4c8 #c9a24a #9a3b2e |
| Act III | dread | cold blue-grey night | the red of Qutuz's coat | low, dark | ~35% | #2b3544 #6d7a8c #7a1f1f |

Hex swatches are suggestions for reference boards. Check them on a generated still before relying on them.

## Risks

- **A child in chains in the market.** Image and video models can refuse or misrender this Cheaper alternative: Keep the chain as a plain cuff, stay on the boy's face and sound, show the other children only as background
- **A body on the marble (Aybak).** The model may add a wound or blood Cheaper alternative: State no blood, no wound; keep his face away from camera until the one calm high-angle shot
- **Adult and child Qutuz.** The two designs can drift toward each other Cheaper alternative: Separate tags and separate references; the market clip never includes the adult
- **Left and right across the extension cuts.** Positions flip between the first part and its extension Cheaper alternative: Each brief records the positions; the extension header restates them
- **The oversized throne and robe.** Scale props drift and the boy stops looking small Cheaper alternative: Lock it in IMPORTANT and use high angles on Ali
- **On-screen text.** Models draw unreliable lettering Cheaper alternative: Add the three text cards and the end card in the edit
- **Dense dialogue in a 30 second clip.** Lip-sync can rush when the request is shorter than the speech Cheaper alternative: Request the duration given in each brief and keep silences in the cuts

## Unknowns (not in the script)

- The visual style was not stated for the episode. "2D anime" is used because the skill describes characters without images as "2D anime style"; change it if the series looks different.
- Voices for the Elder Emir, Dealer, Buyer and Rider were not given.
- What the tent contains besides the torch and the map of Syria.
- Whether the three scenes with text cards should use a different card design from the end card.

## Assumptions made

- 16:9 at 1080p, audio on.
- Slow, solemn delivery at about 2.5 words per second.
- Tags follow the character-location skill: @Name in PascalCase, the same as the sheet file names.
- Each scene is one generation; the two long scenes (2 and 3) are a generation plus an extension.

## Assembly notes

- Generate in the order above. An `extend` clip starts from the previous clip's exact final frame.
- When joining a generation and its extension in an editor, cut where the extension begins so no frame repeats.
- Keep one loudness target across all clips. Streaming platforms commonly normalise near -14 LUFS with true peak around -1 dBTP. Verify against the destination's current specs.
- Run `review-checklist.md` on every generated clip before it goes into the edit.
