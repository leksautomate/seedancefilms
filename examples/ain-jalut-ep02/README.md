# Worked example: Ain Jalut, Episode 02

- `script.txt`: the episode script in the production layout.
- `prompts.json`: scene prompts, sheets (7 characters, 5 locations, 2 extras), and settings (`visual_style`, `language_lock`, `wps`).

```
python3 studio.py examples/ain-jalut-ep02/script.txt --prompts examples/ain-jalut-ep02/prompts.json --wps 2.5 --yes
```

The prompts were written by hand from the script (no model was run), then filed and checked by the program. Anything the script does not state
is marked `(proposed)`. The style "2D anime" was inferred, so change `visual_style` and the sheet fields if the series looks different.
