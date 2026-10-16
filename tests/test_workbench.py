import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tests.helpers import SAMPLE, ROOT
from seedance_agent import cli
from seedance_agent.workbench import TOOLS, Workbench, sync_agents_md

EXAMPLE = ROOT / "examples" / "ain-jalut-ep02"
SCRIPT = (EXAMPLE / "script.txt").read_text(encoding="utf-8")
DATA = json.loads((EXAMPLE / "prompts.json").read_text(encoding="utf-8"))
ORDER = ["S00", "S01", "S02a", "S02b", "S03a", "S03b", "S04"]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = str(Path(self.tmp.name) / "output")
        self.wb = Workbench(self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def start(self):
        r = self.wb.call("start_episode", {"script": SCRIPT, "visual_style": "2D anime", "language_lock": True, "wps": 2.5})
        self.assertTrue(r["ok"], r)
        self.m, self.e = r["movie"], r["episode"]
        return r

    def prompt(self, sid, **kw):
        sub = DATA["prompts"][sid]
        args = {"movie": self.m, "episode": self.e, "segment_id": sid, "prompt": sub["prompt"], "shots": sub["shots"], "brief": sub["brief"],
                "carry_over": sub["carry_over"], "assumptions": sub["assumptions"]}
        args.update(kw)
        return self.wb.call("submit_segment_prompt", args)

    def sheets_and_extras(self):
        sh = DATA["sheets"]
        for c in sh["characters"]:
            self.assertTrue(self.wb.call("submit_sheet", {"movie": self.m, "episode": self.e, "kind": "character", "entry": c})["saved"])
        for l in sh["locations"]:
            self.assertTrue(self.wb.call("submit_sheet", {"movie": self.m, "episode": self.e, "kind": "location", "entry": l})["saved"])
        self.assertTrue(self.wb.call("set_extras", {"movie": self.m, "episode": self.e, "extras": sh["extras"]})["saved"])


class Intake(Base):
    def test_an_unknown_movie_is_asked_for(self):
        r = self.wb.call("start_episode", {"script": SAMPLE.replace('EPISODE 1 - "THE SIX"\n', "")})
        self.assertFalse(r["ok"])
        self.assertEqual(r["needs"], "movie")
        self.assertIn("do not guess", r["ask"])
        self.assertFalse(Path(self.out).exists() and any(Path(self.out).iterdir()))

    def test_the_movie_comes_from_the_script_when_it_names_one(self):
        r = self.wb.call("start_episode", {"script": SCRIPT, "visual_style": "2D anime"})
        self.assertEqual((r["ok"], r["movie"], r["episode"]), (True, "Ain Jalut - The Spring of Goliath", 2))

    def test_the_style_is_asked_for_once(self):
        r = self.wb.call("start_episode", {"script": SCRIPT})
        self.assertEqual([a["need"] for a in r["ask_the_person"]], ["visual_style"])
        self.assertIn("visual style", r["next"])
        r = self.wb.call("start_episode", {"script": SCRIPT, "visual_style": "2D anime"})
        self.assertTrue(r["resumed"])
        self.assertEqual(r["ask_the_person"], [])
        self.assertEqual(self.wb.list_movies()["movies"][0]["visual_style"], "2D anime")

    def test_a_typo_in_the_movie_name_is_confirmed_not_filed_twice(self):
        self.wb.call("start_episode", {"script": SAMPLE, "movie": "The Six"})
        r = self.wb.call("start_episode", {"script": SAMPLE.replace("Roxie", "Roxy"), "movie": "The Sixx"})
        self.assertEqual(r["needs"], "confirm_movie")
        self.assertEqual(r["did_you_mean"], ["The Six"])
        r = self.wb.call("start_episode", {"script": SAMPLE.replace("Roxie", "Roxy"), "movie": "The Sixx", "confirm_new_movie": True})
        self.assertTrue(r["ok"])
        self.assertEqual(r["movie"], "The Sixx")

    def test_the_same_plain_script_resumes_the_same_episode(self):
        a = self.wb.call("start_episode", {"script": SAMPLE, "movie": "The Six"})
        b = self.wb.call("start_episode", {"script": SAMPLE, "movie": "The Six"})
        self.assertEqual((a["episode"], b["episode"], b["resumed"]), (1, 1, True))
        self.assertEqual(len(self.wb.list_movies()["movies"][0]["episodes"]), 1)

    def test_clips_carry_the_spoken_lines_and_the_overlays(self):
        r = self.start()
        self.assertEqual([c["id"] for c in r["clips"]], ORDER)
        first = r["clips"][0]
        spoken = [e["text"] for e in first["events"] if e["kind"] == "dialogue"]
        self.assertEqual(spoken[0], "They will say a slave took the throne of Egypt.")
        self.assertEqual(first["edit_overlays_not_for_the_model_to_draw"], ["Damascus. Many years earlier."])
        self.assertEqual(r["speakers_and_their_scenes"]["QUTUZ"], [0, 2, 3, 4])


class Gates(Base):
    def setUp(self):
        super().setUp()
        self.start()

    def test_a_sheet_without_its_style_or_fields_is_refused(self):
        bad = dict(DATA["sheets"]["characters"][1], lock="")
        r = self.wb.call("submit_sheet", {"movie": self.m, "episode": self.e, "kind": "character", "entry": bad})
        self.assertFalse(r["saved"])
        self.assertIn("Missing field(s): lock.", r["errors"])
        self.assertFalse((Path(self.out) / self.m / "Episode 02 - The Slave Who Would Rule" / "characters" / "@QutuzChild.md").exists())

    def test_the_voice_rule_is_decided_by_the_script(self):
        lead = dict(DATA["sheets"]["characters"][0])
        lead.pop("voice")
        r = self.wb.call("submit_sheet", {"movie": self.m, "episode": self.e, "kind": "character", "entry": lead})
        self.assertFalse(r["saved"])
        self.assertTrue(r["needs_voice_design_prompt"])

    def test_a_clip_cannot_be_written_before_the_one_it_extends(self):
        r = self.prompt("S02b")
        self.assertFalse(r["saved"])
        self.assertIn("Submit S02a first", r["error"])

    def test_changed_dialogue_is_refused_and_nothing_is_saved(self):
        self.sheets_and_extras()
        bad = DATA["prompts"]["S00"]["prompt"].replace("A boy cannot lift a sword.", "A boy cannot lift a blade.")
        r = self.wb.call("check_prompt", {"movie": self.m, "episode": self.e, "segment_id": "S00", "prompt": bad})
        self.assertFalse(r["passes"])
        r = self.prompt("S00", prompt=bad)
        self.assertFalse(r["saved"])
        self.assertTrue(any("word for word" in x for x in r["errors"]))
        self.assertEqual(self.wb.call("episode_status", {"movie": self.m, "episode": self.e})["progress"]["clips_ok"], 0)

    def test_save_anyway_files_it_for_review(self):
        self.sheets_and_extras()
        bad = DATA["prompts"]["S00"]["prompt"].replace("A boy cannot lift a sword.", "A boy cannot lift a blade.")
        r = self.prompt("S00", prompt=bad, save_anyway=True)
        self.assertEqual((r["saved"], r["status"]), (True, "needs-review"))

    def test_no_tags_before_the_sheets_means_the_default_tags_are_required(self):
        r = self.wb.call("check_prompt", {"movie": self.m, "episode": self.e, "segment_id": "S00", "prompt": DATA["prompts"]["S00"]["prompt"]})
        self.assertFalse(r["passes"])   # the studio rules want the sheet tags; the prompt uses @Qutuz, which does not exist yet

    def test_unknown_names_come_back_as_errors_not_crashes(self):
        self.assertFalse(self.wb.call("nope", {})["ok"])
        self.assertFalse(self.wb.call("episode_status", {"movie": "No Such", "episode": 1})["ok"])
        self.assertFalse(self.wb.call("episode_status", {"movie": self.m, "episode": 9})["ok"])
        self.assertFalse(self.wb.call("submit_segment_prompt", {"movie": self.m, "episode": self.e, "segment_id": "S99", "prompt": "x"})["ok"])
        self.assertFalse(self.wb.call("start_episode", {"script": "  "})["ok"])


class WholeEpisode(Base):
    def test_the_host_agent_route_gives_the_same_files_as_the_standalone_program(self):
        self.start()
        a = self.wb.call("submit_story_analysis", {"movie": self.m, "episode": self.e, "analysis": DATA["analysis"]})
        self.assertTrue(a["saved"], a)
        self.sheets_and_extras()
        for sid in ORDER:
            r = self.prompt(sid)
            self.assertTrue(r["saved"], (sid, r))
            self.assertEqual(r["status"], "ok")
        f = self.wb.call("finish_episode", {"movie": self.m, "episode": self.e})
        self.assertTrue(f["ok"], f)
        self.assertEqual((f["clips"], f["clips_ok"], f["clips_needs_review"], f["sheets_needing_review"]), (7, 7, [], []))
        ep = Path(f["path"])
        self.assertEqual(len(list((ep / "characters").glob("@*.md"))), 7)
        self.assertEqual(len(list((ep / "locations").glob("@*.md"))), 5)
        self.assertTrue((ep / "plan.html").exists() and (ep / "README.md").exists())
        self.assertFalse((ep / "_history").exists(), "regenerated overview files must not pile up in _history")
        # the standalone program, fed the same material, files identical prompts
        other = Path(self.tmp.name) / "other"
        from seedance_agent.console import ScriptedConsole
        from seedance_agent.pipeline import Options, run_episode
        run_episode(SCRIPT, Options(output=str(other), prompts_file=str(EXAMPLE / "prompts.json"), wps=2.5), ScriptedConsole(interactive=False), None)
        twin = next(other.glob("*/Episode 02*"))
        for f1 in sorted(ep.glob("Scene*/S*.txt")) + sorted(ep.glob("characters/*.md")) + sorted(ep.glob("locations/*.md")):
            self.assertEqual(f1.read_text(encoding="utf-8"), (twin / f1.relative_to(ep)).read_text(encoding="utf-8"), f1.name)

    def test_a_revision_keeps_the_old_version(self):
        self.start()
        self.wb.call("submit_story_analysis", {"movie": self.m, "episode": self.e, "analysis": DATA["analysis"]})
        self.sheets_and_extras()
        self.prompt("S00")
        new = DATA["prompts"]["S00"]["prompt"].replace("The single torch is the ONLY light source", "The single torch is the only light source in the tent")
        self.assertTrue(self.prompt("S00", prompt=new)["saved"])
        ep = next(Path(self.out).glob("*/Episode 02*"))
        self.assertIn("in the tent", (ep / "Scene 00 - Hook" / "S00_single.txt").read_text(encoding="utf-8"))
        old = list((ep / "_history").rglob("S00_single.txt"))
        self.assertEqual(len(old), 1)
        self.assertNotIn("in the tent", old[0].read_text(encoding="utf-8"))


class Guides(Base):
    def test_guides(self):
        self.start()
        for name in ("workflow", "story_analysis", "sheets", "prompt_writing", "revising"):
            self.assertTrue(self.wb.call("get_guide", {"name": name})["text"].strip())
        g = self.wb.call("get_guide", {"name": "prompt_writing", "movie": self.m, "episode": self.e})["text"]
        self.assertIn("This movie", g)
        self.assertIn("Ain Jalut", g)
        self.assertIn("ask the person directly in the chat", g)
        self.assertFalse(self.wb.call("get_guide", {"name": "nope"})["ok"])

    def test_camera_recipe(self):
        r = self.wb.call("lookup_camera_recipe", {"scene_type": "dialogue"})
        self.assertIn("SCENE RECIPE", r["recipe"])


class McpServer(Base):
    def rpc(self, proc, id_, method, params=None):
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}) + "\n")
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    def test_protocol_over_stdio(self):
        proc = subprocess.Popen([sys.executable, str(ROOT / "studio.py"), "mcp", "--output", self.out], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, cwd=str(ROOT))
        try:
            init = self.rpc(proc, 1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}})["result"]
            self.assertEqual(init["protocolVersion"], "2025-06-18")
            self.assertEqual(init["serverInfo"]["name"], "seedance-studio")
            self.assertIn("You are the Seedance Studio agent", init["instructions"])   # the host learns what this is without being told
            self.assertIn("Never guess the movie name", init["instructions"])
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            tools = self.rpc(proc, 2, "tools/list")["result"]["tools"]
            self.assertEqual([t["name"] for t in tools], list(TOOLS))
            for t in tools:
                self.assertEqual(t["inputSchema"]["type"], "object")
                self.assertTrue(t["description"])
            r = self.rpc(proc, 3, "tools/call", {"name": "start_episode", "arguments": {"script": SAMPLE.replace('EPISODE 1 - "THE SIX"\n', "")}})["result"]
            body = json.loads(r["content"][0]["text"])
            self.assertEqual(body["needs"], "movie")
            r = self.rpc(proc, 4, "tools/call", {"name": "start_episode", "arguments": {"script": SCRIPT, "visual_style": "2D anime"}})["result"]
            self.assertFalse(r["isError"])
            self.assertEqual(json.loads(r["content"][0]["text"])["movie"], "Ain Jalut - The Spring of Goliath")
            r = self.rpc(proc, 5, "tools/call", {"name": "episode_status", "arguments": {"movie": "Nope", "episode": 1}})["result"]
            self.assertTrue(r["isError"])
            self.assertIn("error", self.rpc(proc, 6, "tools/call", {"name": "bogus", "arguments": {}}))
            self.assertEqual(self.rpc(proc, 7, "ping")["result"], {})
            self.assertEqual(self.rpc(proc, 8, "prompts/list")["result"]["prompts"][0]["name"], "new_episode")
            self.assertEqual(self.rpc(proc, 9, "resources/list")["result"], {"resources": []})
            self.assertEqual(self.rpc(proc, 10, "no/such")["error"]["code"], -32601)
        finally:
            proc.stdin.close()
            proc.wait(timeout=10)
        err = proc.stderr.read()
        proc.stdout.close()
        proc.stderr.close()
        self.assertEqual(err, "")


class ShellRoute(Base):
    def run_cli(self, *argv, stdin=None):
        buf = io.StringIO()
        with redirect_stdout(buf), mock.patch.object(sys, "stdin", io.StringIO(stdin or "")):
            code = cli.main(["call", "--output", self.out, *argv])
        return code, buf.getvalue()

    def test_call_lists_the_tools(self):
        code, out = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("submit_segment_prompt", out)

    def test_call_runs_a_tool_with_a_script_file(self):
        code, out = self.run_cli("start_episode", '{"visual_style": "2D anime"}', "--script-file", str(EXAMPLE / "script.txt"))
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["episode"], 2)
        code, out = self.run_cli("episode_status", stdin='{"movie": "Ain Jalut - The Spring of Goliath", "episode": 2}')
        self.assertEqual(json.loads(out)["progress"]["clips"], 7)

    def test_needs_is_not_a_failure_but_an_error_is(self):
        code, out = self.run_cli("start_episode", "--file", self.write_args({"script": SAMPLE.replace('EPISODE 1 - "THE SIX"\n', "")}))
        self.assertEqual((code, json.loads(out)["needs"]), (0, "movie"))
        code, _ = self.run_cli("bogus", "{}")
        self.assertEqual(code, 1)
        code, out = self.run_cli("list_movies", "{not json")
        self.assertEqual(code, 2)

    def write_args(self, d):
        p = Path(self.tmp.name) / "args.json"
        p.write_text(json.dumps(d), encoding="utf-8")
        return str(p)


class DiscoveryFiles(unittest.TestCase):
    """What a host reads on its own when it opens this folder."""

    def test_agents_md_holds_the_current_workflow(self):
        self.assertTrue(sync_agents_md(ROOT / "AGENTS.md", check=True), "run: python3 studio.py sync-agents")

    def test_agents_md_opens_with_the_role(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("You are the Seedance Studio agent", text)
        self.assertIn("You write prompts only. You never generate video", text)

    def test_claude_and_gemini_point_to_agents_md(self):
        for f in ("CLAUDE.md", "GEMINI.md"):
            self.assertEqual((ROOT / f).read_text(encoding="utf-8").strip(), "@AGENTS.md")

    def test_mcp_configs_start_the_server(self):
        for f, key in ((".mcp.json", "mcpServers"), (".cursor/mcp.json", "mcpServers"), (".gemini/settings.json", "mcpServers"), (".vscode/mcp.json", "servers")):
            cfg = json.loads((ROOT / f).read_text(encoding="utf-8"))[key]["seedance-studio"]
            self.assertEqual(cfg["command"], "python3", f)
            self.assertEqual(cfg["args"], ["studio.py", "mcp"], f)
            self.assertTrue((ROOT / cfg["args"][0]).exists())


if __name__ == "__main__":
    unittest.main()
