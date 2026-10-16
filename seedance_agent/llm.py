"""A small, provider-neutral chat client with tool calling. No third-party packages.

Two providers are supported through their plain HTTP APIs:
  anthropic  https://api.anthropic.com/v1/messages
  openai     any OpenAI-compatible /chat/completions endpoint (OpenAI, OpenRouter, a local server ...)

Neutral message format used everywhere in the agent:
  {"role": "user", "content": "text"}
  {"role": "assistant", "content": "text", "tool_calls": [ToolCall, ...]}
  {"role": "tool", "results": [{"id": ..., "name": ..., "content": "text", "is_error": bool}, ...]}
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


class LLMError(Exception):
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class Reply:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = ""
    usage: dict = field(default_factory=dict)


class LLM:
    provider = "base"
    model = ""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0

    def complete(self, system: str, messages: list[dict], tools: list[dict], max_tokens: int = 8000) -> Reply:
        raise NotImplementedError

    def _count(self, inp: int, out: int) -> None:
        self.calls += 1
        self.input_tokens += int(inp or 0)
        self.output_tokens += int(out or 0)


def _post(url: str, headers: dict, body: dict, timeout: int = 300, retries: int = 4) -> dict:
    data = json.dumps(body).encode("utf-8")
    delay = 2.0
    last = ""
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers={**headers, "content-type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            payload = e.read().decode("utf-8", "replace")
            last = "HTTP %s: %s" % (e.code, payload[:500])
            if e.code in (408, 409, 429, 500, 502, 503, 504, 529) and attempt < retries:
                wait = float(e.headers.get("retry-after") or delay) if e.headers else delay
                time.sleep(min(wait, 60))
                delay *= 2
                continue
            raise LLMError(last)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = "network error: %s" % e
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise LLMError(last)
    raise LLMError(last)


class AnthropicLLM(LLM):
    provider = "anthropic"

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.anthropic.com"):
        super().__init__()
        self.api_key, self.model, self.base_url = api_key, model, base_url.rstrip("/")

    def _convert(self, messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                blocks = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for tc in m.get("tool_calls", []):
                    blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.args})
                out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "(no text)"}]})
            elif m["role"] == "tool":
                out.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": r["id"], "content": r["content"], "is_error": bool(r.get("is_error"))}
                    for r in m["results"]]})
        return out

    def complete(self, system, messages, tools, max_tokens=8000):
        body = {"model": self.model, "max_tokens": max_tokens, "system": system, "messages": self._convert(messages)}
        if tools:
            body["tools"] = [{"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]} for t in tools]
        j = _post(self.base_url + "/v1/messages", {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}, body)
        text, calls = [], []
        for b in j.get("content", []):
            if b.get("type") == "text":
                text.append(b.get("text", ""))
            elif b.get("type") == "tool_use":
                calls.append(ToolCall(b["id"], b["name"], b.get("input") or {}))
        usage = j.get("usage", {})
        self._count(usage.get("input_tokens"), usage.get("output_tokens"))
        stop = j.get("stop_reason", "")
        if stop == "max_tokens" and calls:
            raise LLMError("The reply was cut off at max_tokens while calling a tool. Try a larger limit.")
        return Reply("".join(text), calls, stop, usage)


class OpenAILLM(LLM):
    provider = "openai"

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"):
        super().__init__()
        self.api_key, self.model, self.base_url = api_key, model, base_url.rstrip("/")
        self.token_param = "max_tokens"

    def _convert(self, system: str, messages: list[dict]) -> list[dict]:
        out = [{"role": "system", "content": system}]
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                msg = {"role": "assistant", "content": m.get("content") or None}
                if m.get("tool_calls"):
                    msg["tool_calls"] = [{"id": tc.id, "type": "function",
                                          "function": {"name": tc.name, "arguments": json.dumps(tc.args)}} for tc in m["tool_calls"]]
                out.append(msg)
            elif m["role"] == "tool":
                for r in m["results"]:
                    out.append({"role": "tool", "tool_call_id": r["id"], "content": r["content"]})
        return out

    def complete(self, system, messages, tools, max_tokens=8000):
        body = {"model": self.model, "messages": self._convert(system, messages), self.token_param: max_tokens}
        if tools:
            body["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                                "parameters": t["input_schema"]}} for t in tools]
        headers = {"authorization": "Bearer " + self.api_key}
        try:
            j = _post(self.base_url + "/chat/completions", headers, body)
        except LLMError as e:
            # newer OpenAI models want max_completion_tokens; older and local servers want max_tokens
            other = "max_completion_tokens" if self.token_param == "max_tokens" else "max_tokens"
            if "max_completion_tokens" in str(e) or (self.token_param == "max_completion_tokens" and "max_tokens" in str(e)):
                self.token_param = other
                body[other] = body.pop("max_tokens" if other == "max_completion_tokens" else "max_completion_tokens")
                j = _post(self.base_url + "/chat/completions", headers, body)
            else:
                raise
        try:
            choice = j["choices"][0]
            msg = choice["message"]
        except (KeyError, IndexError):
            raise LLMError("Unexpected response: %s" % json.dumps(j)[:300])
        calls = []
        for tc in msg.get("tool_calls") or []:
            raw = tc["function"].get("arguments") or "{}"
            try:
                args = json.loads(raw)
            except json.JSONDecodeError:
                args = {"_unparsed_arguments": raw}
            calls.append(ToolCall(tc["id"], tc["function"]["name"], args))
        usage = j.get("usage", {})
        self._count(usage.get("prompt_tokens"), usage.get("completion_tokens"))
        if choice.get("finish_reason") == "length" and calls:
            raise LLMError("The reply was cut off while calling a tool. Try a larger limit.")
        return Reply(msg.get("content") or "", calls, choice.get("finish_reason", ""), usage)


class ScriptedLLM(LLM):
    """A model stand-in for tests: `fn(system, messages, tools)` returns the next Reply."""

    provider = "scripted"
    model = "scripted"

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def complete(self, system, messages, tools, max_tokens=8000):
        self._count(0, 0)
        return self.fn(system, messages, tools)


DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-4.1"}


def make_llm(provider: str | None = None, model: str | None = None, base_url: str | None = None) -> LLM:
    """Build a client from arguments and environment variables.

    ANTHROPIC_API_KEY, OPENAI_API_KEY, SEEDANCE_PROVIDER, SEEDANCE_MODEL, ANTHROPIC_BASE_URL, OPENAI_BASE_URL
    """
    env = os.environ
    provider = (provider or env.get("SEEDANCE_PROVIDER") or "").lower()
    if not provider:
        provider = "anthropic" if env.get("ANTHROPIC_API_KEY") else ("openai" if env.get("OPENAI_API_KEY") else "")
    if provider == "anthropic":
        key = env.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError("ANTHROPIC_API_KEY is not set.")
        return AnthropicLLM(key, model or env.get("SEEDANCE_MODEL") or DEFAULT_MODELS["anthropic"],
                            base_url or env.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com")
    if provider == "openai":
        key = env.get("OPENAI_API_KEY")
        if not key:
            raise LLMError("OPENAI_API_KEY is not set.")
        return OpenAILLM(key, model or env.get("SEEDANCE_MODEL") or DEFAULT_MODELS["openai"],
                         base_url or env.get("OPENAI_BASE_URL") or "https://api.openai.com/v1")
    raise LLMError("No model is configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY (and optionally SEEDANCE_MODEL), "
                   "or run with --offline to draft prompts from templates without a model.")
