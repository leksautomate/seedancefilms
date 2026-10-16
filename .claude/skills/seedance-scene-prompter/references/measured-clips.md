# Measured timing from five published clips

Source: five finished episodes supplied by the user (19 to 46 seconds each, 1080p, with a ~1 second
end card). Transcribed with Whisper `small.en` (word timestamps), shot cuts found with ffmpeg scene
detection. Use these numbers to calibrate `scripts/dialogue_timing.py`.

Transcript caveats: the recognizer spells character names by sound ("Roxy" for Roxie, "Abe!" for Babe!),
laughs are not counted as words, and "200" was counted as two spoken words ("two hundred").
Times are in seconds from the start of each clip.

## Transcripts

### Cash counting (20.4s)
| Time | Line |
|---|---|
| 1.78-2.56 | Is that enough, babe? |
| 3.07-4.01 | For rent, yeah. |
| 5.20-7.70 | Who is it? |
| 8.78-10.68 | Well, rent isn't due until Friday. |
| 15.72-16.08 | Stay here. |

### Couch and sneakers (27.4s)
| Time | Line |
|---|---|
| 2.00-2.52 | Babe! |
| 3.18-3.46 | No. |
| 4.08-5.28 | I didn't even ask yet! |
| 5.66-6.64 | You want the 200 bucks? |
| 6.92-7.10 | Yes! |
| 7.32-9.08 | Because Cartoon Hero closes in 12 hours! |
| 9.42-9.90 | Still no. |
| 10.92-11.36 | Okay. |
| 12.10-12.84 | Okay, what? |
| 16.02-16.54 | Yeah! |
| 16.78-17.94 | I'll just sell your sneakers. |
| 20.42-20.94 | Jesus. |
| 21.48-22.24 | Give me my wallet. |
| 22.52-23.18 | Aww, babe! |
| 23.34-24.00 | You're the best! |
| 24.42-25.12 | I said wallet. |
| 25.48-25.94 | Not a hug. |

### Waterfall bridge (46.5s)
| Time | Line |
|---|---|
| 0.08-2.34 | (Oh wow!) Just look! |
| 4.60-5.04 | You like it? |
| 5.20-6.06 | Are you kidding, babe? |
| 6.44-7.96 | It's the best date ever! |
| 8.98-9.88 | Happy anniversary, Rox. |
| 20.14-23.92 | Wait, are you sure those bastards won't find us here? |
| 24.48-26.82 | As long as nobody knows we're here, yeah. |
| 28.23-28.67 | What? |
| 32.22-35.99 | Roxie, give me the phone. |
| 37.19-37.57 | Rox! |
| 37.81-38.97 | I only posted one picture! |
| 39.31-39.99 | You posted it? |
| 40.41-41.17 | It's bad, right? |
| 43.53-44.21 | Now we're in trouble. |

### Raven and drone (20.2s)
| Time | Line |
|---|---|
| 5.26-11.54 | Wow, so cool. That's strange. I haven't seen one of these in years. Roxie, don't... |
| 17.20-18.76 | (partly unclear) "...oh shit" |

### Restaurant and pig (36.8s)
| Time | Line |
|---|---|
| 0.91-3.92 | Babe! This is the new Chinese place I told you about! |
| 7.52-7.76 | Fine. |
| 16.94-19.80 | Okay, this is not how I imagined it. |
| 20.83-21.03 | Diesel? |
| 22.21-22.79 | Hey Rufus. |
| 23.35-25.75 | (laughing) My little Diesel! |
| 28.75-31.10 | (laughing) We still doing that thing tonight, right? |
| 33.63-34.07 | What thing? |

## Speaking rate

Sentences of 4 or more words with a clean timestamp span (17 sentences, 107 words, 31 seconds of speech):

- Pooled rate: **3.4 words per second** (median 4.0, middle half 3.1 to 4.9).
- Calm or deadpan lines run slower: "Okay, this is not how I imagined it." 2.8, "Wait, are you sure those bastards won't find us here?" 2.6, "For rent, yeah." 3.2.
- Energetic or comic lines run faster: "You want the 200 bucks?" 6.1, "Are you kidding, babe?" 4.7, "I'll just sell your sneakers." 4.3, "Give me my wallet." 5.3.
- Back-and-forth exchanges including the gaps between lines: 3.1 to 3.8 words per second (couch 4.08-9.90: 22 words in 5.8s; couch 21.48-25.98: 17 words in 4.5s; bridge 4.60-7.96: 12 words in 3.4s; cash 1.78-4.01: 7 words in 2.2s).

Guidance for `--wps`: 3.4 default, 2.5 to 3.0 for slow, deadpan or dramatic delivery, 4.0 for frantic comedy.

## Words per 15 seconds

Spoken words in the first 15 seconds of each published clip: cash 16, couch 26, bridge 23, raven 16.
Typical range 16 to 26. Plan for about 25 or fewer.

## Shot length

74 shots across the five clips: mean 1.95s, median 1.73s, middle 80% between 0.9s and 3.4s.
Shots per 15 seconds: 5.6 to 8.8 (cash 5.6, restaurant 7.1, bridge 8.1, couch 8.6, raven 8.8).

## One shot checked against its prompt

Cash clip, shot 2 (prompt: "Is that enough, babe?" / "For rent? Yeah."): the shot ran 1.38s to 4.92s (3.5s).
Speech started 0.4s after the cut, the two lines ended at 4.01s, and the shot held another 0.9s. So a
dialogue shot lasts roughly speaking time plus 1 to 1.3 seconds of lead-in and tail when there is a visual beat.
The script's estimate (speaking time plus 0.3s padding) is the minimum for tightly cut shots; add about 0.5s per
dialogue shot when a shot also needs a reaction or action beat.
