"""A Model Context Protocol server (stdio) that gives any MCP-capable assistant the studio's tools.

Claude Code, Gemini CLI, Antigravity, Cursor, VS Code and others start this process themselves from a small config file
(see .mcp.json) and read its `instructions`, so the assistant knows what the studio is and how to work without being told.

Messages are JSON-RPC 2.0, one per line, on stdin and stdout. Nothing else may be written to stdout. No packages needed.
"""
from __future__ import annotations

import json
import os
import sys

from . import prompts
from .workbench import TOOLS, Workbench

NAME = "seedance-studio"
VERSION = "1.0.0"
DEFAULT_PROTOCOL = "2025-06-18"
SUPPORTED = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")

INSTRUCTIONS = prompts.load("workflow.md")


def _reply(id_, result=None, error=None) -> dict:
    msg = {"jsonrpc": "2.0", "id": id_}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    return msg


class Server:
    def __init__(self, output: str | None = None):
        self.bench = Workbench(output or os.environ.get("SEEDANCE_OUTPUT", "output"))

    def handle(self, msg: dict) -> dict | None:
        method, id_, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
        if method is None:  # a response to something we never sent
            return None
        is_notification = "id" not in msg
        try:
            if method == "initialize":
                wanted = params.get("protocolVersion")
                return _reply(id_, {"protocolVersion": wanted if wanted in SUPPORTED else DEFAULT_PROTOCOL,
                                    "capabilities": {"tools": {"listChanged": False}, "prompts": {"listChanged": False}},
                                    "serverInfo": {"name": NAME, "version": VERSION, "title": "Seedance Studio"},
                                    "instructions": INSTRUCTIONS})
            if method == "ping":
                return _reply(id_, {})
            if method == "tools/list":
                return _reply(id_, {"tools": [{"name": n, "description": d, "inputSchema": schema} for n, (d, schema) in TOOLS.items()]})
            if method == "tools/call":
                name, args = params.get("name"), params.get("arguments") or {}
                if name not in TOOLS:
                    return _reply(id_, error={"code": -32602, "message": "Unknown tool: %s" % name})
                result = self.bench.call(name, args)
                return _reply(id_, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=1)}],
                                    "isError": not result.get("ok", False) and "error" in result})
            if method == "prompts/list":
                return _reply(id_, {"prompts": [{"name": "new_episode", "title": "New episode",
                                                 "description": "Turn a pasted episode script into checked Seedance 2.5 prompts, sheets and files.",
                                                 "arguments": [{"name": "script", "description": "The episode script", "required": False}]}]})
            if method == "prompts/get":
                if params.get("name") != "new_episode":
                    return _reply(id_, error={"code": -32602, "message": "Unknown prompt"})
                script = (params.get("arguments") or {}).get("script", "")
                text = "Follow the Seedance Studio workflow for this episode script.\n\n" + (script or "Ask me to paste the episode script, then follow the workflow.")
                return _reply(id_, {"description": "New episode", "messages": [{"role": "user", "content": {"type": "text", "text": text}}]})
            if method in ("resources/list", "resources/templates/list"):
                return _reply(id_, {"resources": []} if method == "resources/list" else {"resourceTemplates": []})
            if method.startswith("notifications/"):
                return None
            if is_notification:
                return None
            return _reply(id_, error={"code": -32601, "message": "Method not found: %s" % method})
        except Exception as e:  # a tool must never take the server down
            if is_notification:
                return None
            return _reply(id_, error={"code": -32603, "message": "%s: %s" % (type(e).__name__, e)})


def serve(inp=None, out=None, output: str | None = None) -> None:
    inp, out = inp or sys.stdin, out or sys.stdout
    server = Server(output)
    for line in inp:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            out.write(json.dumps(_reply(None, error={"code": -32700, "message": "Parse error"})) + "\n")
            out.flush()
            continue
        for m in (msg if isinstance(msg, list) else [msg]):
            resp = server.handle(m)
            if resp is not None:
                out.write(json.dumps(resp, ensure_ascii=False) + "\n")
                out.flush()


def main() -> int:
    serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
