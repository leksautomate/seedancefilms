# Shot Flow Patterns

> English adaptation of `shot-flow-patterns.md` from cinematic-camera-engine by yzsp-ai (MIT). See `../ATTRIBUTION.md`.
> Durations below are the original's guidance for AI video. For dialogue comedy in this project use the fast
> variants (average shot 1.7-2.7s measured); see the Local notes in `../SKILL.md`.

Detailed expansion of the 8 classic shot sequences: a standard flow, variants, rhythm parameters, notes for
AI video, and worked examples. After the quick-reference table in STEP 4 names a template, get the execution
details here.

---

## General rhythm rules

| Rule | Description |
|---|---|
| **Breathing rule** | After a fast-cut run (each shot 2s or less), place a long shot (4s or more) so the audience can breathe |
| **Steady opening** | The first shot of a group should be 3s or more with a locked or slow move so the audience can "enter" the scene |
| **Closing landing** | The last shot of a group should be 3s or more, giving a sense of landing |
| **Scale jumps** | Adjacent shots differ by at least 2 scale levels (medium to extreme close-up works, medium to medium close-up does not) |
| **Movement direction** | Two consecutive shots must not move 180 degrees opposite (move left then move right makes the audience dizzy) |
| **Density changes gradually** | Cuts get denser or sparser step by step; avoid random fluctuation (fast, slow, fast, slow = chaos) |

### Notes for AI video
- Recommended single-shot length 3-8s (the models' best controllable range).
- Shots over 8s tend to distort motion; consider splitting into 2 shots.
- In fast-cut runs (each shot 2s or less) make sure each shot's subject and action are simple (one job per shot).
- Scale jumps matter even more in AI video: a 1-level jump can generate nearly the same composition.

---

## Template 1: Progressive Reveal

**For:** character entrance, establishing a place, opening sequence, moving from unknown to known

### Standard flow
```
Shot 1: Wide Shot - locked 3-5s - establish the space
Shot 2: Full Shot - slow push 3-4s - lock the figure's position in the space
Shot 3: Medium Shot - locked or slight push 3-4s - face first appears, basic information
Shot 4: Close-up - locked 2-3s - the memorable feature (expression or signature object)
```

### Variants

**A. Mystery reveal** (part first, whole later)
```
Shot 1: Extreme close-up - a detail (hand / foot / object), unknown whose, 3s
Shot 2: Medium - half the body shown, still partly hidden, 3s
Shot 3: Full - fully revealed, 4s
Shot 4: Close-up - face and signature feature, 3s
```
Change: the scale order is reversed (close, then wide, then close), creating "clue first, answer later" suspense.

**B. Environment reveal** (peeling back the space layer by layer)
```
Shot 1: Extreme wide - macro geography (city / mountains / sea), 5s
Shot 2: Wide - a specific area (one building / one street), 4s
Shot 3: Medium - inside the space (room / corner), 3s
Shot 4: Extreme close-up - a key object in the space (a letter on the desk, a photo on the wall), 3s
```

**C. Accelerating reveal** (rhythm speeds up)
```
Shot 1: Wide - 5s (slowest, fully absorbed)
Shot 2: Full - 3s (faster)
Shot 3: Medium - 2s (faster again)
Shot 4: Close-up - 1.5s (fastest, impact)
```
For entrances with growing urgency (a villain appears, an arrival against the clock).

### Rhythm parameters
| Parameter | Standard | Tense variant | Calm variant |
|---|---|---|---|
| Total length | 12-16s | 8-10s | 16-22s |
| Single shot | 3-4s | 1.5-3s | 4-6s |
| Moving share | 50% | 30% | 60% |

---

## Template 2: Emotional Focus

**For:** emotion building step by step, a character's inner change, a decisive moment, from reason to feeling

### Standard flow
```
Shot 1: Medium Shot - locked 3s - character in the environment, emotion still controlled
Shot 2: Medium Close-up - slight push 3s - start reading facial detail
Shot 3: Close-up - locked 3-4s - emotion fills the frame
Shot 4: Extreme Close-up - locked 2-3s - the final extreme expression (tears / trembling lip / pupils)
```

### Variants

**A. Outburst type** (acceleration plus interruption)
```
Shot 1: Medium - 3s - calm
Shot 2: Close-up - 2s - (skip the medium close-up, speeding up the focus)
Shot 3: Extreme close-up - 1.5s - extreme expression
Shot 4: Wide - sudden pull out 4s - (emptiness and aftermath of the outburst)
```
Change: the big scale jump between shot 3 and 4 (extreme close-up to wide) creates an emotional break.

**B. Parallel emotion contrast** (two characters' emotions escalate together)
```
Shot 1: Two-shot medium - 3s - both in frame, establish the relationship
Shot 2: Character A close-up - 2s - A's reaction
Shot 3: Character B close-up - 2s - B's reaction
Shot 4: Character A extreme close-up - 2s - A's emotion peaks
Shot 5: Character B extreme close-up - 2s - B's emotion peaks
Shot 6: Two-shot medium - 3s - back to the relationship (now changed)
```

**C. Silent emotion** (pure visual storytelling, no dialogue)
```
Shot 1: Locked medium long take - 5s - character looks calm on the surface
Shot 2: Close-up with very slow push - 5s - drawn into the inner life
Shot 3: Locked extreme close-up - 4s - a tiny change of expression is the only "action"
```
For inner scenes, the silence before breaking down, a silent collapse.

### Rhythm parameters
| Parameter | Standard | Rapid variant | Immersive variant |
|---|---|---|---|
| Total length | 11-14s | 7-9s | 14-20s |
| Single shot | 2-4s | 1.5-2.5s | 3-5s |
| Moving share | 30% | 20% | 40% (very slow) |

---

## Template 3: Shocking Reveal

**For:** revealing the truth, showing scale, a twist, the "so that's it" moment

### Standard flow
```
Shot 1: Close-up (character reaction) - locked 2-3s - shock / fear / disbelief
Shot 2: Fast pull out to wide / full - 0.5-1.5s - reveal what caused the reaction
Shot 3: Back to close-up (character absorbs it) - 3-4s - understanding / acceptance / breakdown
```

### Variants

**A. Double reveal** (half first, then everything)
```
Shot 1: Close-up reaction - 2s
Shot 2: Medium half-reveal - 2s - (audience sees only part)
Shot 3: More shocked close-up reaction - 1.5s
Shot 4: Fast pull out to wide, full reveal - 1.5s
```

**B. Dolly Zoom reveal** (warped-space type)
```
Shot 1: Medium - Dolly Zoom 3s - (background pulls close but the subject does not grow, Vertigo effect)
Shot 2: Wide - sudden cut 1s - (the true shape of the warped space)
```
Note: AI models support Dolly Zoom only partly; in the prompt describe it as `background warping while subject stays fixed`.

**C. Delayed reveal** (build anticipation, then answer)
```
Shot 1: Close-up reaction - 3s - (what did the character see? the audience does not know yet)
Shot 2: Character's body language changes - medium 3s - (step back? step forward? tremble?)
Shot 3: Very slow push toward the revealed thing - wide to medium 5s - (finally revealed)
```

### Rhythm parameters
| Parameter | Standard | Rapid impact | Slow-burn reveal |
|---|---|---|---|
| Total length | 6-10s | 4-6s | 10-16s |
| Reaction shot | 2-3s | 1-2s | 3-5s |
| Reveal shot | 0.5-2s | 0.5-1s | 3-5s |

---

## Template 4: Standard Dialogue

**For:** standard conversation, everyday exchange, passing information

### Standard flow
```
Shot 1: Two-shot medium - locked 3-4s - establish the two people's spatial relationship
Shot 2: Shot A - over-the-shoulder medium close-up 3-4s - A speaks
Shot 3: Reverse B - over-the-shoulder medium close-up 3-4s - B responds
Shot 4: Shot A - close-up 2-3s - A's key reaction
Shot 5: Two-shot medium - locked 3s - return to the relationship, close the passage
```

### Variants

**A. Interleaved** (break the monotony of shot/reverse-shot)
```
Shot 1: Two-shot medium - 3s
Shot 2: Shot A (over the shoulder) - 3s
Shot 3: Insert extreme close-up (hand / object / environment detail) - 2s - (breaks the rhythm)
Shot 4: Reverse B (over the shoulder) - 3s
Shot 5: Side-angle two-shot medium - 3s - (a two-shot from a new angle)
```

**B. Walking dialogue** (talking while walking)
```
Tracking shot throughout, two-shot medium
Occasional cut to a single close-up to read the expression
On the key line the character stops: locked close-up
```

**C. Three or more people**
```
Shot 1: Wide of the three - establish spatial relationships
Shots 2-4: Single medium close-ups of each speaker in turn
Shot 5: Reaction close-up of the listener (key - the silent person's reaction is often more important)
Shot 6: Back to the wide
```
Note: avoid pure shot/reverse-shot in group dialogue; it reads like watching table tennis. After every 3-4 shot/reverse-shot cuts, insert a wide or a reaction close-up.

### Rhythm parameters
| Parameter | Standard | Fast | Slow |
|---|---|---|---|
| Shot/reverse-shot length | 3-4s | 2-3s | 4-6s |
| Two-shot length | 3-4s | 2-3s | 4-5s |
| Shot/reverse-shot to other ratio | 60:40 | 70:30 | 50:50 |

---

## Template 5: Escalating Dialogue

**For:** arguments, interrogation, standoff, from calm to outburst

### Standard flow
```
Phase 1 (calm):
  Shot 1: Two-shot medium - locked 4s - surface peace
  Shots 2-3: Shot/reverse-shot medium close-ups - 3-4s each - normal conversation rhythm

Phase 2 (heating up):
  Shots 4-5: Shot/reverse-shot tightened to close-up - 2-3s each - (tighter scale = rising pressure)
  Movement: add a slight push (slow push of 10-15% per shot)

Phase 3 (outburst):
  Shot 6: Single extreme close-up - slight handheld shake 2s - expression out of control
  Shot 7: Opponent's extreme close-up - 1.5s - reaction to the blow
  Shot 8: Two-shot medium (side or rear, a new angle) - 3s - the new composition says the relationship has changed
```

### Variants

**A. Cold-war escalation** (no outburst, but ever colder)
```
Scale stays medium to medium close-up throughout (never tightens to extreme close-up)
But movement goes from locked to a gradually slower push in
Tone goes warm to cold
Last shot: two-shot medium, the space between the two clearly bigger (physical distance = psychological distance)
```

**B. One-sided pressure** (one side dominates, the other is pressed)
```
Dominant side: always medium to medium close-up, eye level or slight low, steady
Pressed side: tightening from medium to extreme close-up, increasingly slight high angle, unstable movement
Intercut: the two characters' "camera treatment" difference = the power difference
```

### Rhythm parameters
| Parameter | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Single shot | 3-4s | 2-3s | 1.5-2s |
| Movement | Locked | Slight push | Handheld |
| Scale | Medium to medium close-up | Medium close-up to close-up | Close-up to extreme close-up |

---

## Template 6: Action Sequence

**For:** fights, chases, battles, sports

### Standard flow
```
Shot 1: Wide - locked 3-4s - establish the battlefield / chase route
Shot 2: Medium - handheld follow 2-3s - the core action
Shot 3: Extreme close-up - locked or fast push 1-2s - the moment of impact (fist / explosion / collision)
Shot 4: Wide - locked 3s - the result / aftermath
```

### Variants

**A. Continuous chase** (non-stop motion)
```
Shot 1: Wide tracking - Steadicam follows the runner 4s
Shot 2: POV - the chaser's view 2s
Shot 3: Medium - a key action node such as a corner or jump 2s
Shot 4: Wide - show the gap (caught up or pulling away) 3s
Loop shots 2-4 until the chase ends
```

**B. One-on-one fight**
```
Shot 1: Wide two-shot - standoff 3s
Shots 2-5: Alternating medium close-ups - rounds of attack and defense, 1.5-2s each
Shot 6: Extreme close-up - the deciding blow 1s
Shot 7: Wide - result (one side falls) 3s
```

**C. Slow-motion accent** (slow the key moment)
```
In a normal-speed action flow, insert one slow-motion extreme close-up at the moment of impact (0.5-1s stretched to 2-3s)
Return to normal speed right after the slow shot so the contrast makes impact
At most 1-2 slow-motion points per sequence (more causes fatigue)
```

### Rhythm parameters
| Parameter | Standard | Brutal impact | Elegant martial arts |
|---|---|---|---|
| Single shot | 2-3s | 1-1.5s | 3-5s |
| Moving share | 80% | 90% | 60% |
| Main movement | Handheld + slide | Handheld + whip pan | Steadicam + orbit |
| Establish / result shot | 3-4s | 2-3s | 4-5s |

---

## Template 7: Loneliness / Departure

**For:** goodbyes, leaving, facing something alone, loss, regret

### Standard flow
```
Shot 1: Close-up - locked 3-4s - catch the last emotional expression
Shot 2: Slow pull out to wide - 5-8s - the character gradually shrinks in the frame
```

### Variants

**A. Drifting apart**
```
Shot 1: Two-shot close-up - 3s - the last intimacy
Shot 2: Single medium - the character turns and leaves 3s
Shot 3: Locked wide - the back view grows smaller 5-8s
Shot 4: Extreme wide - the character vanishes into the environment 3-5s (optional)
```

**B. The one left behind** (view from the side of the one who stays)
```
Shot 1: Over-the-shoulder medium - from behind the stayer's shoulder, watching the leaver 3s
Shot 2: Close-up - the stayer's expression (watching them go / holding back / breaking) 4s
Shot 3: POV - the stayer sees the empty door / road / seat 3s
Shot 4: Wide - the stayer standing alone in the space 5s
```

**C. Death / final parting**
```
Shot 1: Two-shot close-up - the last look / touch 5s (long take, no cut)
Shot 2: Extreme close-up - fingers letting go / eyes closing 3s
Shot 3: Very slow pull out to wide - 8-10s - let the act of "leaving" carry the story
(no movement changes throughout, only the pull out)
```

### Rhythm parameters
| Parameter | Standard | Restrained | Breaking down |
|---|---|---|---|
| Total length | 8-15s | 6-10s | 12-20s |
| Pull-out speed | Very slow (5-8s) | Moderately slow (3-5s) | Very slow (8-10s) |
| Locked shot length | 3-4s | 2-3s | 4-5s |
| Movement | Slow pull | Slow pull | Slow pull + slight rise (overview) |

---

## Template 8: Ensemble Climax

**For:** team assembling, celebrating victory, final showdown, everyone's reveal

### Standard flow
```
Shots 1-N: Close-up cuts of each character - 1-2s each - shown one by one
Shot N+1: Full / wide - orbit or crane 4-6s - everyone in one frame
```

### Variants

**A. Assembly** (from scattered to together)
```
Shot 1: Character A medium - walking in from one direction 2s
Shot 2: Character B medium - from another direction 2s
Shot 3: Character C medium - from a third direction 2s
Shot 4: Full - the three meet in the center 4s
Shot 5: Crane up to bird's eye - show the full lineup 3s
```

**B. Emotional resonance** (different expressions of one feeling)
```
Shot 1: Character A close-up - smiling 1.5s
Shot 2: Character B close-up - smiling through tears 1.5s
Shot 3: Character C close-up - silent nod 1.5s
Shot 4: Character D close-up - laughing out loud 1.5s
Shot 5: Full - everyone together, orbit shot 5s
```
Change: each close-up has a different reaction but the same emotional core, creating the feeling of "different roads, same destination".

**C. All-out battle**
```
Shot 1: Full - the whole standoff 3s
Shots 2-5: Quick-cut mediums of each character - fighting stance / weapon, 1s each
Shot 6: Wide - everyone charges / collective action 4s
Shot 7: Mixed medium close-ups - each fighter's highlight, 1-2s each
Shot 8: Full - the dust settles 4s
```

### Rhythm parameters
| Parameter | 2-3 people | 4-6 people | 7+ people |
|---|---|---|---|
| Per-person shot | 2-3s | 1.5-2s | 1-1.5s |
| Wide shot | 4-5s | 5-6s | 6-8s |
| Total length | 8-14s | 12-18s | 15-25s |

---

## Chaining templates

Real scenes often chain several templates. Common combinations:

| Scene | Template chain | Total length reference |
|---|---|---|
| Character entrance, then dialogue | Progressive reveal, Standard dialogue | 25-35s |
| Dialogue, then argument, then fight | Standard dialogue, Escalating dialogue, Action sequence | 35-50s |
| Establish the environment, character entrance, inner monologue | Progressive reveal (environment), Progressive reveal (character), Emotional focus | 30-45s |
| Team assembles, battle, victory | Ensemble climax (assembly), Action sequence, Ensemble climax (celebration) | 40-60s |
| Discover the truth, emotional collapse, departure | Shocking reveal, Emotional focus, Loneliness / departure | 25-40s |

### Chaining transition rules
- Put **one transition shot** (2-3s) between templates to bridge different emotional passages.
- Good transition shots: an environment empty shot (sky / water / building), a silent medium of a character, a close-up of an object.
- Between two high-intensity templates (action into action) there must be a landing shot of 3s or more.
- From a slow template to a fast one: the transition shot uses a short move to "start up" the acceleration.
- From a fast template to a slow one: the transition shot uses a long locked-off shot to "brake".
