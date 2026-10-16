# Scene to Camera Recipes

> English adaptation of `scene-camera-recipes.md` from cinematic-camera-engine by yzsp-ai (MIT). See `../ATTRIBUTION.md`.

12 core scene types. Each gives a **default camera plan, mood variants, and an AI prompt fragment**.
Once the STEP 0 decision tree names the scene type, take the full plan from this file.

---

## 1. Dialogue

**Triggers:** talk / chat / argue / confess / interrogate / negotiate / persuade

### Default plan (everyday dialogue)
| Element | Plan |
|---|---|
| Establishing shot | Two-shot medium (Medium Two-Shot) showing the spatial relationship |
| Alternating subjects | Shot/reverse-shot, medium close-up, over-the-shoulder framing |
| Emotional peak | Insert a close-up or extreme close-up to read the reaction |
| Movement | 90% locked-off, a slow push only at emotional turns |
| Angle | Eye level |
| Lens | 50-85mm |

### Mood variants
| Mood | Adjustment |
|---|---|
| Warm / intimate | Tighten shot/reverse-shot to close-up, 85mm for blur, warm light |
| Tense / standoff | Scale tightens from medium to extreme close-up as conflict rises, add a slight push, 85-135mm |
| Argument / outburst | Slight handheld shake, medium quickly tightening to close-up, faster rhythm, occasional whip pan between characters |
| Interrogation / pressure | Interrogator low angle + subject high angle, locked-off camera for pressure, inserts on sweat or fingers |
| Confession / deep feeling | Two-shot medium, then slow push to a single close-up, 85mm shallow depth, soft background |

### Prompt fragment (standard dialogue)
```
Medium two-shot of two characters facing each other at a café table, 50mm lens, eye-level, soft natural lighting. Cut to over-the-shoulder medium close-up of Character A speaking, 85mm lens, shallow depth of field.
```

---

## 2. Action

**Triggers:** fight / chase / escape / explosion / battle / car chase / combat

### Default plan
| Element | Plan |
|---|---|
| Opening | Wide shot establishing the space and participants |
| Action process | Medium to medium close-up capturing the action, handheld follow |
| Moment of impact | Close-up on the hit point, explosion, or key action |
| Result | Wide or medium showing the outcome |
| Movement | Handheld 80%, whip pan between characters, fast push to stress a hit |
| Angle | Low angles for power, mix of eye level and low |
| Lens | 24-50mm to capture the range of motion |

### Mood variants
| Mood | Adjustment |
|---|---|
| Heroic / fiery | Mostly low angle, crane moves for ceremony, slow-motion close-up on the hit |
| Chaotic / panic | Extremely unsteady handheld, 15 degree Dutch angle, fast cuts (each shot under 2s) |
| One against many | Orbit shot showing the encirclement, hero low angle (low angle = stronger) |
| Chase | Side-tracking follow, Steadicam, speed first, occasional POV |

### Prompt fragment
```
Wide shot establishing a rain-soaked alley, two figures facing off, 28mm lens, low angle. Handheld medium shot tracking the first punch, camera shakes on impact. Extreme close-up of fist connecting with jaw, motion blur on impact, 35mm lens.
```

---

## 3. Inner monologue

**Triggers:** monologue / memory / thinking / staring / hesitation / struggle / resolve

### Default plan
| Element | Plan |
|---|---|
| Main scale | Close-up to extreme close-up (read the face) |
| Secondary scale | Wide (the character's smallness and loneliness in the space) |
| Movement | Very slow push (3-5s) drawing the viewer into the mind |
| Angle | Eye level or slight high (vulnerability) |
| Lens | 85-135mm, very shallow depth, background fully blurred |

### Mood variants
| Mood | Adjustment |
|---|---|
| Memory / nostalgia | Soft focus, slow push medium to close-up, warm tones |
| Pain / struggle | Close-up plus slight Dutch tilt (5-10 degrees), light handheld tremor |
| Awakening / resolve | Shift from slight high to eye level to slight low (power rises), slow push to eyes in close-up |
| Despair / giving up | Locked-off wide (person in an empty space), very long hold (5s or more without cutting) |

### Prompt fragment
```
Close-up of character's face, 100mm lens, extremely shallow depth of field, background dissolved into warm bokeh. Slow dolly in over 4 seconds from medium close-up to tight close-up, ending on eyes glistening with unshed tears. Eye-level angle, minimal movement.
```

---

## 4. Character entrance

**Triggers:** walks in / arrives / enters / comes to / appears / pushes the door / steps in

### Default plan
| Element | Plan |
|---|---|
| Sequence | Progressive reveal: wide (silhouette or part) to full (whole figure) to medium (face first seen) to close-up (memorable feature) |
| Movement | Side-slide or slow push following the character |
| Angle | Slight low (goodwill, anticipation) |
| Lens | Wide 35mm tightening to close-up 85mm |

### Mood variants
| Mood | Adjustment |
|---|---|
| Imposing / boss | Start on a close-up of footsteps, slow pull to a full shot, low angle, slow pace |
| Mysterious / suspense | Silhouette wide, then detail close-ups (hand, shoe), face last, backlight |
| Surprise / joy | Whip pan from another character's surprised reaction to a full shot of the entrant |
| Casual / relaxed | Medium side-follow as they walk in, natural rhythm |

### Prompt fragment (imposing entrance)
```
Extreme close-up of polished black shoes stepping onto marble floor. Slow tilt up revealing tailored suit legs. Wide shot from low angle as the figure walks toward camera down a grand corridor, 24mm lens, imposing silhouette against backlight.
```

---

## 5. Environment establishing

**Triggers:** city / mountain / ocean / building / space / room / world

### Default plan
| Element | Plan |
|---|---|
| Scale | Extreme wide or wide |
| Movement | Slow slide or crane (aerial feel), 2-5s |
| Angle | Eye level or bird's eye |
| Lens | 14-35mm ultra wide to wide |
| Duration | 3s or more so the audience can "read" the space |

### Mood variants
| Mood | Adjustment |
|---|---|
| Grand / epic | Extreme wide + bird's-eye crane, 14mm ultra wide, golden hour light |
| Oppressive / post-apocalyptic | Wide + high-angle overlook, grey tones, locked-off camera held a long time |
| Warm / home | Wide, then slow push into a medium (toward a building or window), warm light |
| Dangerous / unknown | Slow push into a dark space, slight handheld, wide-angle distortion for unease |

### Prompt fragment
```
Extreme wide shot of a sprawling cyberpunk city at dusk, 16mm ultra-wide lens, bird's eye view slowly panning right, neon lights reflecting on wet streets, dense vertical architecture fading into smog.
```

---

## 6. Character introduction

**Triggers:** first appearance / debut / introduced / introduce a character

### Default plan
| Element | Plan |
|---|---|
| Sequence | Full shot establishing (character in the environment), medium shot placing (build, costume, bearing), extreme close-up on the memorable detail (scar, accessory, gaze) |
| Movement | Full locked-off, medium slow push, close-up locked-off |
| Angle | By personality: hero = slight low, villain = low, ordinary person = eye level |
| Lens | Full shot 35mm, close-up 100mm |

### How this differs from "character entrance"
- **Character entrance** = a physical action (walking in), stressing spatial movement.
- **Character introduction** = a story event (the first time the audience meets this character), stressing a memorable feature.

### Prompt fragment
```
Full shot of a woman standing at the edge of a rooftop, 35mm lens, wind blowing her coat, city skyline behind. Cut to medium shot revealing her calm, scarred face, 50mm lens. Extreme close-up on her distinctive silver ring as she taps it against the railing, 100mm lens.
```

---

## 7. Farewell / ending

**Triggers:** parting / leaving / ending / death / goodbye / last meeting

### Default plan
| Element | Plan |
|---|---|
| Sequence | Close-up (catch the last emotion), then slow pull out to wide (the person shrinks in the space) |
| Movement | Slow Pull Out 3-8s, optionally with a crane |
| Angle | Eye level moving to slight high (bystander view) |
| Lens | 85mm (close-up) to 35mm (pulled out to wide) |

### Mood variants
| Mood | Adjustment |
|---|---|
| Grief / death | Locked close-up held 5s or more, then a very slow pull out, no other movement so the feeling can settle |
| Relief / calm | Medium slow pull matching the character turning away, natural light |
| Reluctance / lingering | Two-shot medium to single close-up to slow pull to a wide silhouette |
| Hope / new start | Slow pull to a wide as the character walks toward the light, slight low angle |

### Prompt fragment
```
Close-up of two hands slowly separating, 85mm lens, shallow depth of field. Slow pull out over 5 seconds revealing the character standing alone on an empty train platform, transitioning to wide shot, 35mm lens, the figure growing smaller as the camera retreats.
```

---

## 8. Revelation

**Triggers:** discovers / reveals / truth / shock / twist / "so that's it"

### Default plan
| Element | Plan |
|---|---|
| Sequence | Close-up (reaction, shocked face), then fast pull out to wide or full (reveal the whole) |
| Movement | Fast Pull Out 0.5-1.5s, or Dolly Zoom 2-3s |
| Angle | Eye level, then adjust to what is revealed (threat = low, the whole picture = bird's eye) |
| Lens | Close-up 100mm snapping to full 24mm |

### Mood variants
| Mood | Adjustment |
|---|---|
| Shock / fear | Dolly Zoom (background pulls closer while the camera retreats), Dutch angle |
| Moved / relieved | Slow pull (not fast), close-up of eyes with tears to a warm wide |
| Surprise | Whip pan from the character's reaction to the revealed object, fast rhythm |
| Horror reveal | Very slow push toward the revealed thing, 5s or more, building anxious waiting |

### Prompt fragment (shock type)
```
Extreme close-up of character's eyes widening in shock, 100mm lens, pupils dilating. Dolly zoom effect over 2 seconds as the background warps and stretches, creating vertigo sensation, the character's face remains in frame while the world distorts behind them.
```

---

## 9. Static emotion

**Triggers:** waiting / loneliness / boredom / emptiness / daydreaming / silence / sitting still

### Default plan
| Element | Plan |
|---|---|
| Main scale | Wide (character small in a big space) |
| Secondary scale | Extreme close-up (fingers, mouth corner, eyes) to break visual monotony |
| Movement | Mostly locked-off (80% or more), stressing stillness and emptiness |
| Angle | Eye level or slight high |
| Lens | Wide 28mm alternating with close-up 100mm |
| Rhythm | Slow, each shot 3s or more, letting "emptiness" itself carry the meaning |

### Mood variants
| Mood | Adjustment |
|---|---|
| Waiting / expectant | Locked medium, character looking out of frame (implies the thing waited for) |
| Lonely / abandoned | Locked extreme wide, tiny figure, huge space, 5s or more |
| Numb / worn out | Locked eye-level, no movement, close-up on a face with no change of expression |
| Inner struggle | Locked close-up long take, tiny facial changes are the only motion |

### Prompt fragment
```
Wide shot of a lone figure sitting on a park bench, 28mm lens, eye-level, vast empty park stretching behind, autumn leaves scattered, completely still frame held for 5 seconds. Cut to extreme close-up of fingers absently picking at the bench paint, 100mm lens.
```

---

## 10. Ensemble climax

**Triggers:** celebration / cheering / victory / reunion / assembling / everyone

### Default plan
| Element | Plan |
|---|---|
| Sequence | Fast close-up cuts of each character (1-2s each), then a full/wide shot holding everyone |
| Movement | Close-ups locked and fast-cut, the wide with orbit or crane |
| Angle | Close-ups at eye level, the wide at slight low or bird's eye |
| Lens | Close-ups 85mm, the wide 24mm |

### Mood variants
| Mood | Adjustment |
|---|---|
| Victory / fiery | Low-angle full shot + crane rising to bird's eye, rhythm from fast cuts to a slow wide |
| Warm / reunion | Medium orbit so each character enters the frame naturally |
| Solemn / assembling | Close-ups of firm faces, then a slow pull to a wide showing the size of the group |
| Chaos / angry crowd | Fast handheld cuts, each character under 1s, a high-angle wide over the chaos |

### Prompt fragment
```
Quick cuts: close-up of Character A smiling, 85mm lens, 1 second. Close-up of Character B raising fist, 1 second. Close-up of Character C wiping tears, 1 second. Wide shot crane up revealing all characters standing together on a hilltop at sunset, 24mm lens, slow rise from eye-level to slight bird's eye, golden hour light.
```

---

## 11. Transition / montage

**Triggers:** transition / time passing / montage / day to night / growth / training

### Default plan
| Element | Plan |
|---|---|
| Scale | Mixed: change scale on every cut (wide, close, medium, wide, close ...) |
| Movement | Short moves (1-2s push, pull, slide) for a flowing feel |
| Angle | Varied, a different angle on each shot |
| Lens | Change focal length per shot to avoid visual repetition |
| Rhythm | Fast cuts (1-3s each), whole sequence 10-30s |

### Mood variants
| Mood | Adjustment |
|---|---|
| Growth / progress | Cuts accelerate from slow to fast, scale moves from wide to close (approaching the goal) |
| Time passing | Locked camera with the same composition while content changes (day, night, day), dissolve transitions |
| Decline / decay | Gradually add Dutch angles, scale moves from close to wide (away from the core), tone goes cold and dark |
| Happy memory | Soft focus / overexposed, warm, mostly medium, light rhythm |

### Prompt fragment
```
Montage sequence: Medium shot of hands kneading dough, 50mm lens, 2 seconds. Wide shot of the bakery at dawn, 28mm lens, 1.5 seconds. Close-up of flour dusting a finished loaf, 85mm lens, 1.5 seconds. Medium shot of character wiping forehead with satisfied smile, 50mm lens, 2 seconds. Each shot connected by matching motion cuts.
```

---

## 12. Suspense / horror

**Triggers:** fear / stalking / spying / danger / shadows / darkness / eerie

### Default plan
| Element | Plan |
|---|---|
| Main viewpoint | Alternate POV (first person) and objective shots |
| Scale | Wide (the unknown in the space) to close-up (fear reaction) in big jumps |
| Movement | Light handheld shake (unease) + very slow push (the dread of waiting) |
| Angle | Dutch 15-30 degrees (imbalance), low angle (the threat looks bigger) |
| Lens | Wide 24mm (space distorts fear) + tele 200mm (spied-on feeling) |

### Mood variants
| Mood | Adjustment |
|---|---|
| Stalking / watched | 200mm locked wide (the watcher's view), leaves or a door gap as foreground cover |
| Confined / claustrophobic | 14mm ultra wide (warped space) + low angle + walls closing in |
| Jump scare | Long locked shot (5s or more building safety), then a sudden whip pan or fast push to the source of fear |
| Psychological horror | Dolly Zoom (warped space), close-up of the face with the background slowly changing |

### Prompt fragment (stalking type)
```
Long telephoto shot (200mm) through chain-link fence, voyeuristic perspective watching a woman walk down an empty street at night, compressed perspective flattening the depth. Cut to her POV close-up looking over shoulder, 35mm handheld with slight shake, seeing nothing but shadows. Dutch angle medium shot of the empty street behind her, tilted 20 degrees, streetlight flickering.
```

---

## How to use

1. After the STEP 0 tree names the scene type, take the "Default plan" from this file.
2. Combine it with the "emotional tone" extracted in STEP 0 and adjust from the "Mood variants".
3. Prompt fragments can be pasted straight into a timecoded video prompt.
4. Mixed scenes (for example "a fight breaks out during a conversation"): use scene 1's plan for the first half and scene 2's plan after the turning point.
5. A scene that continues more than 30s must add scale variation to the default plan to avoid visual fatigue.
