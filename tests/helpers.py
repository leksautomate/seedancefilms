"""Shared test helpers: a sample script, a scripted model, and fake HTTP."""
from __future__ import annotations

import io
import json
import re
import sys
import urllib.error
from email.message import Message
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from seedance_agent import offline  # noqa: E402
from seedance_agent.llm import Reply, ScriptedLLM, ToolCall  # noqa: E402

SAMPLE = (ROOT / ".claude/skills/episode-segmenter/examples/sample-episode.txt").read_text(encoding="utf-8")


def json_after(text: str, marker: str):
    """The first ```json block after `marker` in a message."""
    i = text.index(marker)
    m = re.search(r"```json\n(.*?)\n```", text[i:], re.S)
    return json.loads(m.group(1))


def good_model(break_first_for: str | None = None, asked: list | None = None) -> ScriptedLLM:
    """A model stand-in that behaves like a good writer: it analyses the story, then writes valid prompts.

    If `break_first_for` is a clip id, its first submission changes one spoken word, so the gate must reject it and the
    model must correct itself.
    """
    state = {"submitted_bad": set()}

    def fn(system, messages, tools):
        names = {t["name"] for t in tools}
        first = messages[0]["content"]
        last = messages[-1]
        # tool results arrive as a 'tool' message; if the last one says accepted, the loop ends by itself
        if "submit_story_analysis" in names:
            if len(messages) == 1:
                plan = json_after(first, "## The segment plan")
                scenes = sorted({p["scene"] for p in plan})
                return Reply("", [ToolCall("a1", "submit_story_analysis", {
                    "logline": "A couple's small domestic quarrels hide a bigger danger.",
                    "tone": "comedic, then tense",
                    "spine": [{"act": "Act I", "scenes": scenes[:3], "note": "Domestic comedy."}, {"act": "Act II", "scenes": scenes[3:], "note": "The danger arrives."}],
                    "scenes": [{"scene": n, "why": "It turns the episode a little further toward the danger.", "scene_type": "dialogue", "mood": "comedic",
                                "camera_approach": "Hard cuts, tighten on the punchline.", "status": "ready"} for n in scenes],
                    "characters": [{"name": "WOLF", "tag": "@ TAG WOLF", "look": "", "voice": "Deep, dry, deadpan male voice.", "source": "assumed"},
                                   {"name": "GIRL", "tag": "@ TAG GIRL", "look": "", "voice": "Bright young British female voice.", "source": "assumed"}],
                    "locations": [{"name": "Kitchen", "tag": "@ TAG KITCHEN"}],
                    "style_lock": "Worn dystopian painterly animation.",
                    "color_script": [{"beat": "Act I", "emotion": "warm irritation", "dominant": "amber", "accent": "pink", "contrast": "medium",
                                      "saturation": "~60%", "hex": ["#c98b3a", "#e4a3b8", "#3b2a1f"]}],
                    "motif": "red light", "risks": [{"item": "Tiny props", "why": "They drift between shots", "alternative": "Keep them in one hand"}],
                    "unknowns": ["Exact apartment layout."], "assumptions": ["16:9"]})])
            return Reply("Done.")
        if "submit_segment_prompt" in names:
            if len(messages) == 1:
                ctx = json_after(first, "Write the prompt for this clip.")
                seg = ctx["segment"]
                events = [{"kind": e["kind"], "speaker": e["speaker"], "text": e["text"], "seconds": e["seconds"]} for e in seg["events"]]
                bible = {"characters": {n: {"tag": c["tag"], "voice": c["voice"]} for n, c in seg["characters"].items()}, "locations": {}}
                s2 = {"id": seg["id"], "mode": seg["mode"], "characters": list(seg["characters"]), "events": events, "request_s": seg["request_s"],
                      "location": seg["location"]["name"].lower(), "part": seg["part"], "parts": seg["parts"]}
                prev = ctx.get("previous_clip")
                d = offline.draft(s2, bible, {"clip_seconds": 15}, prev)
                prompt = d["prompt"]
                if break_first_for == seg["id"] and seg["id"] not in state["submitted_bad"]:
                    state["submitted_bad"].add(seg["id"])
                    prompt = prompt.replace("Then get a bigger size", "Then buy bigger jeans").replace("Whatever", "Fine")
                    if prompt == d["prompt"]:
                        prompt = re.sub(r"“([^”]+)”", lambda m: "“" + m.group(1) + " really”", prompt, count=1)
                state["payload"] = {"segment_id": seg["id"], "prompt": prompt, "shots": d["shots"], "brief": d["brief"],
                                    "carry_over": d["carry_over"], "assumptions": ["Written by the scripted test model."], "_good": d["prompt"]}
                return Reply("", [ToolCall("w1", "submit_segment_prompt", {k: v for k, v in state["payload"].items() if k != "_good"})])
            # the previous submission was rejected: fix it with the good prompt
            payload = dict(state["payload"])
            payload["prompt"] = payload.pop("_good")
            return Reply("", [ToolCall("w%d" % len(messages), "submit_segment_prompt", payload)])
        return Reply("nothing to do")

    return ScriptedLLM(fn)


class FakeResp:
    def __init__(self, obj):
        self._b = json.dumps(obj).encode("utf-8")

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_error(code: int, retry_after: str | None = None) -> urllib.error.HTTPError:
    h = Message()
    if retry_after is not None:
        h["retry-after"] = retry_after
    return urllib.error.HTTPError("http://x", code, "err", h, io.BytesIO(b'{"error":"x"}'))
