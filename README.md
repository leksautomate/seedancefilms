# Seedance films: episode to video prompts

Skills for turning an episode script into Seedance 2.5 prompts, with the dialogue checked against the clip length.
They live in `.claude/skills/`.

| Skill | What it does |
|---|---|
| `episode-segmenter` | Splits an episode into scenes and clip-sized segments (15 s, +15 s extension, new chains, short clips) with estimated seconds and cut points |
| `cinematic-camera-engine` | English adaptation of [yzsp-studio/cinematic-camera-engine](https://github.com/yzsp-studio/cinematic-camera-engine) (MIT): scene and mood to shot plan |
| `seedance-scene-prompter` | Writes the shot-by-shot prompt in the established house style and counts dialogue words to estimate seconds |

The flow and the data passed between the skills are in [`docs/agent-pipeline.md`](docs/agent-pipeline.md).

## Quick start

```
python3 .claude/skills/episode-segmenter/scripts/segment_episode.py .claude/skills/episode-segmenter/examples/sample-episode.txt
python3 .claude/skills/seedance-scene-prompter/scripts/dialogue_timing.py .claude/skills/seedance-scene-prompter/examples/01-kitchen-jeans-15s.txt
```

Both scripts use only the Python standard library.
