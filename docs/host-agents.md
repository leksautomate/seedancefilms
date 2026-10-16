# How an AI assistant knows this is an agent

An assistant does not know what a folder is for. It learns from files it loads on its own, and it can only act through tools it
can call. So an "agent" inside an AI IDE is three things, not one program:

1. **A definition it reads at the start**: who it is, when to act, the steps, the rules. This is `AGENTS.md`.
2. **Tools it can call**: an MCP server (or a shell command) that does the work and refuses bad results. This is
   `seedance_agent/workbench.py`, served by `seedance_agent/mcp_server.py`.
3. **Knowledge it reads when needed**: the writing guide, the sheet guide, the camera recipes. These come from the `get_guide` and
   `lookup_camera_recipe` tools.

The model that writes is the assistant's own. This repository supplies the other two parts.

## What each assistant loads

| Assistant | Reads on its own | Starts the tools from |
|---|---|---|
| Claude Code | `CLAUDE.md` (here: `@AGENTS.md`), or `AGENTS.md` directly in recent versions | `.mcp.json` (it asks you to approve the server once) |
| Gemini CLI | `GEMINI.md` (here: `@AGENTS.md`) | `.gemini/settings.json` |
| Antigravity | `AGENTS.md` and `GEMINI.md`, walking up from the files it works on | Its MCP settings: add the server once (command `python3`, arguments `studio.py mcp`, working directory this folder) |
| Cursor | `AGENTS.md` | `.cursor/mcp.json` |
| VS Code (agent mode) | `AGENTS.md` | `.vscode/mcp.json` |
| Anything else that can run shell commands | `AGENTS.md` if it supports the standard | `python3 studio.py call <tool> '<json>'`, no MCP needed |

When the MCP server connects it also sends the workflow as its `instructions`, so an assistant that never opened `AGENTS.md` still gets
the role and the steps.

## What happens when you paste a script

1. The assistant calls `start_episode` with the script. The tool splits it into clips and files the plan. If the movie is unknown it
   answers `needs: movie`; the assistant must ask you, because the tool will not file anything without it. If the visual style is
   unknown it is asked for once and kept for the movie.
2. The assistant writes the story analysis, shows you the character and location lists (invented details marked `(proposed)`), and
   builds each sheet with `submit_sheet`. A sheet that breaks the skill's rules is rejected with the exact errors.
3. It writes each clip with `check_prompt`, then `submit_segment_prompt`. A prompt that changes a spoken word, misses a tag or the
   language lock, or overruns its time is rejected and nothing is saved.
4. `finish_episode` writes the plan page, README and checklists, and the assistant reports what is ready, what needs review and what
   was assumed.

State lives in the episode folder (`episode.json`), not in the assistant's memory, so a new session or a different assistant can pick
up where the last one stopped (`episode_status`).

## The tools

`list_movies`, `start_episode`, `get_guide`, `lookup_camera_recipe`, `submit_story_analysis`, `submit_sheet`, `set_extras`,
`check_prompt`, `submit_segment_prompt`, `finish_episode`, `episode_status`. `python3 studio.py call` prints this list.

## What has been verified, and what has not

Tested here: the tools, their gates, the whole Ain Jalut episode through them, the MCP protocol over a real stdio process (initialize,
instructions, tool list, tool calls, errors), the shell route, and that `AGENTS.md` matches the workflow text.

Not tested, because those assistants are not available in this environment: that each assistant actually starts the server from its
config file and follows the instructions. The configs follow the documented formats of Claude Code (`.mcp.json`, `AGENTS.md` support),
Gemini CLI (`mcpServers` in settings) and Antigravity (reads `AGENTS.md`/`GEMINI.md`); the `@AGENTS.md` import in `GEMINI.md`, the
Antigravity MCP setup steps, and the Cursor and VS Code files are written from memory of their formats. If one assistant ignores them,
the fallback is always the same: tell it to read `AGENTS.md`, or to run `python3 studio.py call`.
