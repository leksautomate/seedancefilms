"""The agent loop: the model reasons, calls tools, sees the results, and continues until the job is done.

Each tool handler returns a string. A handler that raises is reported to the model as an error result, so the
model can correct itself. `done()` tells the loop the job is complete (for example the prompt was saved).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from .llm import LLM, ToolCall


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    handler: Callable[[dict], str]

    def spec(self) -> dict:
        return {"name": self.name, "description": self.description, "input_schema": self.schema}


@dataclass
class LoopResult:
    messages: list = field(default_factory=list)
    turns: int = 0
    final_text: str = ""
    finished: bool = False
    tool_log: list = field(default_factory=list)


def _missing(schema: dict, args: dict) -> list[str]:
    return [k for k in schema.get("required", []) if k not in args]


def run_loop(llm: LLM, system: str, first_user: str, tools: list[Tool], done: Callable[[], bool] | None = None,
             max_turns: int = 14, max_tokens: int = 8000, nudge: str | None = None, max_nudges: int = 2,
             on_event: Callable[[str], None] | None = None) -> LoopResult:
    by_name = {t.name: t for t in tools}
    specs = [t.spec() for t in tools]
    messages: list[dict] = [{"role": "user", "content": first_user}]
    result = LoopResult(messages=messages)
    nudges = 0
    emit = on_event or (lambda _m: None)

    for _ in range(max_turns):
        reply = llm.complete(system, messages, specs, max_tokens)
        result.turns += 1
        messages.append({"role": "assistant", "content": reply.text, "tool_calls": reply.tool_calls})
        if reply.text:
            result.final_text = reply.text
        if not reply.tool_calls:
            if done and done():
                result.finished = True
                break
            if nudge and nudges < max_nudges:
                nudges += 1
                messages.append({"role": "user", "content": nudge})
                continue
            break
        results = []
        for call in reply.tool_calls:
            tool = by_name.get(call.name)
            if tool is None:
                results.append({"id": call.id, "name": call.name, "content": "Unknown tool %r. Available: %s" % (
                    call.name, ", ".join(by_name)), "is_error": True})
                continue
            miss = _missing(tool.schema, call.args)
            if miss:
                results.append({"id": call.id, "name": call.name, "content": "Missing required field(s): %s" % ", ".join(miss), "is_error": True})
                continue
            emit("tool: %s" % call.name)
            try:
                out = tool.handler(call.args)
                results.append({"id": call.id, "name": call.name, "content": out if isinstance(out, str) else json.dumps(out), "is_error": False})
            except Exception as e:  # report to the model, do not crash the run
                results.append({"id": call.id, "name": call.name, "content": "Tool error: %s" % e, "is_error": True})
            result.tool_log.append(call.name)
        messages.append({"role": "tool", "results": results})
        if done and done():
            result.finished = True
            break
    else:
        result.finished = bool(done and done())
    if done and done():
        result.finished = True
    return result
