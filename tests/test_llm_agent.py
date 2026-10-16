import json
import unittest
from unittest import mock

from tests.helpers import FakeResp, http_error
from seedance_agent import llm as L
from seedance_agent.agent import Tool, run_loop
from seedance_agent.llm import AnthropicLLM, LLMError, OpenAILLM, Reply, ScriptedLLM, ToolCall

TOOLS = [{"name": "t", "description": "d", "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}}]


class AnthropicClient(unittest.TestCase):
    def test_request_and_reply_shape(self):
        seen = {}

        def fake(req, timeout=0):
            seen["url"] = req.full_url
            seen["headers"] = {k.lower(): v for k, v in req.header_items()}
            seen["body"] = json.loads(req.data)
            return FakeResp({"content": [{"type": "text", "text": "hi"}, {"type": "tool_use", "id": "tu1", "name": "t", "input": {"x": "1"}}],
                             "stop_reason": "tool_use", "usage": {"input_tokens": 11, "output_tokens": 7}})

        c = AnthropicLLM("KEY", "claude-test", "https://api.example.com")
        msgs = [{"role": "user", "content": "go"},
                {"role": "assistant", "content": "", "tool_calls": [ToolCall("tu0", "t", {"x": "0"})]},
                {"role": "tool", "results": [{"id": "tu0", "name": "t", "content": "ok", "is_error": False}]}]
        with mock.patch("urllib.request.urlopen", fake):
            r = c.complete("SYS", msgs, TOOLS)
        self.assertEqual(seen["url"], "https://api.example.com/v1/messages")
        self.assertEqual(seen["headers"]["x-api-key"], "KEY")
        self.assertEqual(seen["headers"]["anthropic-version"], "2023-06-01")
        b = seen["body"]
        self.assertEqual((b["model"], b["system"]), ("claude-test", "SYS"))
        self.assertEqual(b["tools"][0]["input_schema"]["required"], ["x"])
        self.assertEqual(b["messages"][1]["content"][0], {"type": "tool_use", "id": "tu0", "name": "t", "input": {"x": "0"}})
        self.assertEqual(b["messages"][2]["content"][0]["type"], "tool_result")
        self.assertEqual(b["messages"][2]["content"][0]["tool_use_id"], "tu0")
        self.assertEqual((r.text, r.tool_calls[0].name, r.tool_calls[0].args), ("hi", "t", {"x": "1"}))
        self.assertEqual((c.input_tokens, c.output_tokens, c.calls), (11, 7, 1))

    def test_truncated_tool_call_is_an_error(self):
        with mock.patch("urllib.request.urlopen", lambda *a, **k: FakeResp(
                {"content": [{"type": "tool_use", "id": "1", "name": "t", "input": {}}], "stop_reason": "max_tokens", "usage": {}})):
            with self.assertRaises(LLMError):
                AnthropicLLM("K", "m").complete("s", [{"role": "user", "content": "x"}], TOOLS)


class OpenAIClient(unittest.TestCase):
    def test_request_and_reply_shape(self):
        seen = {}

        def fake(req, timeout=0):
            seen["url"] = req.full_url
            seen["headers"] = {k.lower(): v for k, v in req.header_items()}
            seen["body"] = json.loads(req.data)
            return FakeResp({"choices": [{"message": {"content": None, "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "t", "arguments": "{\"x\": \"2\"}"}}]}, "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3}})

        c = OpenAILLM("KEY", "gpt-test", "https://example.com/v1")
        msgs = [{"role": "user", "content": "go"},
                {"role": "assistant", "content": "", "tool_calls": [ToolCall("c0", "t", {"x": "0"})]},
                {"role": "tool", "results": [{"id": "c0", "name": "t", "content": "ok"}]}]
        with mock.patch("urllib.request.urlopen", fake):
            r = c.complete("SYS", msgs, TOOLS)
        self.assertEqual(seen["url"], "https://example.com/v1/chat/completions")
        self.assertEqual(seen["headers"]["authorization"], "Bearer KEY")
        b = seen["body"]
        self.assertEqual(b["messages"][0], {"role": "system", "content": "SYS"})
        self.assertEqual(b["messages"][2]["tool_calls"][0]["function"]["arguments"], "{\"x\": \"0\"}")
        self.assertEqual(b["messages"][3], {"role": "tool", "tool_call_id": "c0", "content": "ok"})
        self.assertEqual(b["tools"][0]["function"]["parameters"]["required"], ["x"])
        self.assertEqual(r.tool_calls[0].args, {"x": "2"})
        self.assertEqual((c.input_tokens, c.output_tokens), (5, 3))

    def test_bad_arguments_do_not_crash(self):
        with mock.patch("urllib.request.urlopen", lambda *a, **k: FakeResp({"choices": [{"message": {"content": "", "tool_calls": [
                {"id": "c1", "function": {"name": "t", "arguments": "{not json"}}]}, "finish_reason": "tool_calls"}], "usage": {}})):
            r = OpenAILLM("K", "m").complete("s", [{"role": "user", "content": "x"}], TOOLS)
        self.assertIn("_unparsed_arguments", r.tool_calls[0].args)


class Retries(unittest.TestCase):
    def test_retries_on_429_then_succeeds(self):
        calls = {"n": 0}

        def fake(req, timeout=0):
            calls["n"] += 1
            if calls["n"] < 3:
                raise http_error(429, "0")
            return FakeResp({"content": [{"type": "text", "text": "ok"}], "usage": {}})

        with mock.patch("urllib.request.urlopen", fake), mock.patch("time.sleep"):
            r = AnthropicLLM("K", "m").complete("s", [{"role": "user", "content": "x"}], [])
        self.assertEqual((r.text, calls["n"]), ("ok", 3))

    def test_does_not_retry_a_400(self):
        calls = {"n": 0}

        def fake(req, timeout=0):
            calls["n"] += 1
            raise http_error(400)

        with mock.patch("urllib.request.urlopen", fake), mock.patch("time.sleep"):
            with self.assertRaises(LLMError):
                AnthropicLLM("K", "m").complete("s", [{"role": "user", "content": "x"}], [])
        self.assertEqual(calls["n"], 1)


class Factory(unittest.TestCase):
    def test_picks_provider_from_key(self):
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "a"}, clear=True):
            self.assertEqual(L.make_llm().provider, "anthropic")
        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "o", "SEEDANCE_MODEL": "m1"}, clear=True):
            c = L.make_llm()
            self.assertEqual((c.provider, c.model), ("openai", "m1"))

    def test_no_key_explains_offline(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(LLMError) as cm:
                L.make_llm()
        self.assertIn("--offline", str(cm.exception))


class Loop(unittest.TestCase):
    def test_tool_round_trip_and_error_recovery(self):
        got = []

        def handler(a):
            got.append(a["x"])
            if a["x"] == "bad":
                raise ValueError("nope")
            return "fine"

        tools = [Tool("t", "d", TOOLS[0]["input_schema"], handler)]
        script = [
            Reply("", [ToolCall("1", "t", {"x": "bad"}), ToolCall("2", "missing", {}), ToolCall("3", "t", {})]),
            Reply("", [ToolCall("4", "t", {"x": "good"})]),
        ]
        results_seen = []

        def fn(system, messages, tls):
            if messages[-1]["role"] == "tool":
                results_seen.append(messages[-1]["results"])
            return script.pop(0)

        state = {"done": False}
        tools[0].handler = lambda a: (handler(a), state.update(done=a["x"] == "good"), "fine")[-1]
        res = run_loop(ScriptedLLM(fn), "sys", "go", tools, done=lambda: state["done"])
        self.assertTrue(res.finished)
        first = results_seen[0]
        self.assertTrue(first[0]["is_error"] and "nope" in first[0]["content"])
        self.assertTrue(first[1]["is_error"] and "Unknown tool" in first[1]["content"])
        self.assertTrue(first[2]["is_error"] and "Missing required" in first[2]["content"])
        self.assertEqual(got, ["bad", "good"])

    def test_nudges_a_model_that_stops_early(self):
        state = {"done": False, "n": 0}

        def fn(system, messages, tls):
            state["n"] += 1
            if state["n"] == 1:
                return Reply("I think I am done.")
            return Reply("", [ToolCall("1", "t", {"x": "go"})])

        tools = [Tool("t", "d", TOOLS[0]["input_schema"], lambda a: state.update(done=True) or "ok")]
        res = run_loop(ScriptedLLM(fn), "s", "u", tools, done=lambda: state["done"], nudge="Call t now.")
        self.assertTrue(res.finished)
        self.assertEqual(state["n"], 2)

    def test_stops_at_max_turns(self):
        tools = [Tool("t", "d", TOOLS[0]["input_schema"], lambda a: "ok")]
        res = run_loop(ScriptedLLM(lambda s, m, t: Reply("", [ToolCall("1", "t", {"x": "a"})])), "s", "u", tools, done=lambda: False, max_turns=3)
        self.assertFalse(res.finished)
        self.assertEqual(res.turns, 3)


if __name__ == "__main__":
    unittest.main()


class OpenAITokenParam(unittest.TestCase):
    def test_switches_to_max_completion_tokens_when_the_server_asks(self):
        seen = []

        def fake(req, timeout=0):
            body = json.loads(req.data)
            seen.append(sorted(k for k in body if k.startswith("max")))
            if "max_tokens" in body:
                raise http_error_with_body(400, '{"error":{"message":"Unsupported parameter: max_tokens. Use max_completion_tokens instead."}}')
            return FakeResp({"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {}})

        c = OpenAILLM("K", "m")
        with mock.patch("urllib.request.urlopen", fake):
            r = c.complete("s", [{"role": "user", "content": "x"}], [])
            c.complete("s", [{"role": "user", "content": "x"}], [])
        self.assertEqual(r.text, "ok")
        self.assertEqual(seen, [["max_tokens"], ["max_completion_tokens"], ["max_completion_tokens"]])


def http_error_with_body(code, body):
    import io
    import urllib.error
    from email.message import Message
    return urllib.error.HTTPError("http://x", code, "err", Message(), io.BytesIO(body.encode()))
