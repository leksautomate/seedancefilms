import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import SAMPLE, good_model
from seedance_agent.console import ScriptedConsole
from seedance_agent.intake import NeedInput
from seedance_agent.pipeline import Options, revise_segment, run_episode
from seedance_agent.tools import camera_lookup
from seedance_agent.util import read_json


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = str(Path(self.tmp.name) / "output")

    def tearDown(self):
        self.tmp.cleanup()

    def opts(self, **kw):
        kw.setdefault("clip", 15.0)  # these tests assert the 15 second layout; the default is 30
        kw.setdefault("chain", 30.0)
        return Options(output=self.out, movie=kw.pop("movie", "The Six"), **kw)

    def ep(self, movie="The Six", name="Episode 01 - The Six"):
        return Path(self.out) / movie / name


class Offline(Base):
    def test_folder_structure_and_files(self):
        r = run_episode(SAMPLE, self.opts(offline=True), ScriptedConsole(interactive=False), None)
        ep = self.ep()
        self.assertEqual(r["segments"], 8)
        self.assertEqual(r["ok"], 8)
        for f in ("script.txt", "episode.json", "plan.html", "README.md", "prompts-all.md", "review-checklist.md"):
            self.assertTrue((ep / f).exists(), f)
        self.assertTrue((Path(self.out) / "The Six" / "movie.json").exists())
        scenes = sorted(p.name for p in ep.iterdir() if p.name.startswith("Scene"))
        self.assertEqual(scenes, ["Scene 01 - Kitchen", "Scene 02 - Bedroom", "Scene 03 - Underground City", "Scene 04 - Restaurant", "Scene 05 - Bridge"])
        files = sorted(p.name for p in (ep / "Scene 01 - Kitchen").iterdir())
        self.assertEqual(files, ["S01a_brief.md", "S01a_generate.txt", "S01b_brief.md", "S01b_extend.txt"])
        self.assertFalse((ep / "_history").exists())
        self.assertEqual((ep / "script.txt").read_text(), SAMPLE)

    def test_prompt_files_are_paste_ready_and_keep_the_dialogue(self):
        run_episode(SAMPLE, self.opts(offline=True), ScriptedConsole(interactive=False), None)
        text = (self.ep() / "Scene 01 - Kitchen" / "S01a_generate.txt").read_text()
        self.assertTrue(text.startswith("Create a"))
        self.assertIn("“Do I look fat in these jeans?”", text)
        self.assertNotIn("```", text)
        ext = (self.ep() / "Scene 01 - Kitchen" / "S01b_extend.txt").read_text()
        self.assertTrue(ext.startswith("Extend the @ TAG VIDEO"))
        self.assertIn("Are you SURE? They feel so tight...", ext.split("SHOT 1")[0])

    def test_bible_is_saved_at_movie_level(self):
        run_episode(SAMPLE, self.opts(offline=True), ScriptedConsole(interactive=False), None)
        movie = read_json(Path(self.out) / "The Six" / "movie.json")
        self.assertEqual(movie["bible"]["characters"]["WOLF"]["tag"], "@ TAG WOLF")
        self.assertIn("RUFUS", movie["bible"]["characters"])
        self.assertNotIn("SIX", movie["bible"]["characters"])

    def test_resume_skips_finished_clips(self):
        run_episode(SAMPLE, self.opts(offline=True), ScriptedConsole(interactive=False), None)
        p = self.ep() / "episode.json"
        state = json.loads(p.read_text())
        state["segments"][2]["status"] = "pending"
        state["segments"][2].pop("prompt")
        p.write_text(json.dumps(state))
        lines = []
        con = ScriptedConsole(interactive=False)
        con.say = lines.append
        run_episode(SAMPLE, self.opts(offline=True), con, None)
        joined = "\n".join(lines)
        self.assertIn("Resuming", joined)
        self.assertEqual(joined.count("Writing"), 1)
        self.assertIn("Writing S02a", joined)

    def test_changed_script_keeps_the_old_version(self):
        run_episode(SAMPLE, self.opts(offline=True), ScriptedConsole(interactive=False), None)
        changed = SAMPLE.replace("Do I look fat in these jeans?", "Do these jeans look bad?")
        run_episode(changed, self.opts(offline=True), ScriptedConsole(interactive=False), None)
        hist = list((self.ep() / "_history").rglob("script.txt"))
        self.assertEqual(len(hist), 1)
        self.assertIn("fat in these jeans", hist[0].read_text())
        self.assertIn("Do these jeans look bad?", (self.ep() / "script.txt").read_text())

    def test_second_episode_goes_in_the_same_movie(self):
        run_episode(SAMPLE, self.opts(offline=True), ScriptedConsole(interactive=False), None)
        run_episode(SAMPLE.replace("EPISODE 1", "EPISODE 2"), self.opts(offline=True), ScriptedConsole(interactive=False), None)
        eps = sorted(p.name for p in (Path(self.out) / "The Six").iterdir() if p.name.startswith("Episode"))
        self.assertEqual(eps, ["Episode 01 - The Six", "Episode 02 - The Six"])

    def test_needs_the_movie_name(self):
        with self.assertRaises(NeedInput):
            run_episode(SAMPLE, Options(output=self.out, offline=True), ScriptedConsole(interactive=False), None)

    def test_asks_for_the_movie_when_interactive(self):
        con = ScriptedConsole(["Brand New Movie", ""])
        r = run_episode(SAMPLE, Options(output=self.out, offline=True), con, None)
        self.assertEqual(r["movie"], "Brand New Movie")
        self.assertTrue((Path(self.out) / "Brand New Movie" / "movie.json").exists())

    def test_user_edits_to_the_bible_survive_a_new_episode(self):
        run_episode(SAMPLE, self.opts(offline=True), ScriptedConsole(interactive=False), None)
        mp = Path(self.out) / "The Six" / "movie.json"
        m = json.loads(mp.read_text())
        m["bible"]["characters"]["WOLF"]["tag"] = "@ TAG WOLF_HERO"
        m["bible"]["characters"]["WOLF"]["voice"] = "A custom gravelly voice."
        mp.write_text(json.dumps(m))
        run_episode(SAMPLE.replace("EPISODE 1", "EPISODE 2"), self.opts(offline=True), ScriptedConsole(interactive=False), None)
        text = (self.ep(name="Episode 02 - The Six") / "Scene 01 - Kitchen" / "S01a_generate.txt").read_text()
        self.assertIn("@ TAG WOLF_HERO", text)
        self.assertIn("A custom gravelly voice.", text)

    def test_plan_page_is_self_contained_and_escaped(self):
        run_episode(SAMPLE.replace("Whatever.", "<script>alert(1)</script> & more."), self.opts(offline=True), ScriptedConsole(interactive=False), None)
        html = (self.ep() / "plan.html").read_text()
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertIn("&lt;script&gt;", html)


class WithModel(Base):
    def test_agent_run_with_a_model(self):
        llm = good_model()
        r = run_episode(SAMPLE, self.opts(), ScriptedConsole(interactive=False), llm)
        self.assertEqual((r["segments"], r["ok"]), (8, 8))
        state = read_json(self.ep() / "episode.json")
        self.assertEqual(state["analysis"]["logline"], "A couple's small domestic quarrels hide a bigger danger.")
        movie = read_json(Path(self.out) / "The Six" / "movie.json")
        self.assertEqual(movie["bible"]["characters"]["WOLF"]["voice"], "Deep, dry, deadpan male voice.")
        self.assertEqual(movie["settings"]["style_lock"], "Worn dystopian painterly animation.")
        self.assertGreaterEqual(llm.calls, 9)  # one analysis plus a call per clip
        brief = (self.ep() / "Scene 01 - Kitchen" / "S01a_brief.md").read_text()
        self.assertIn("It turns the episode a little further toward the danger.", brief)
        self.assertIn("Written by the scripted test model.", brief)
        self.assertIn("Act I", (self.ep() / "plan.html").read_text())

    def test_the_gate_forces_the_model_to_fix_changed_dialogue(self):
        llm = good_model(break_first_for="S01a")
        r = run_episode(SAMPLE, self.opts(), ScriptedConsole(interactive=False), llm)
        state = read_json(self.ep() / "episode.json")
        seg = state["segments"][0]
        self.assertEqual(seg["status"], "ok")
        self.assertEqual(seg["attempts"], 2)
        self.assertIn("“Do I look fat in these jeans?”", seg["prompt"])
        self.assertEqual(r["needs_review"], [])

    def test_a_model_that_never_fixes_it_is_saved_for_review(self):
        def stubborn(system, messages, tools):
            names = {t["name"] for t in tools}
            if "submit_story_analysis" in names:
                return good_model().fn(system, messages, tools)
            from seedance_agent.llm import Reply, ToolCall
            from tests.helpers import json_after
            sid = json_after(messages[0]["content"], "Write the prompt for this clip.")["segment"]["id"]
            return Reply("", [ToolCall("x%d" % len(messages), "submit_segment_prompt", {
                "segment_id": sid, "prompt": "SHOT 1\nSHOT 2\nwrong", "shots": [], "brief": {}, "carry_over": {}})])

        from seedance_agent.llm import ScriptedLLM
        r = run_episode(SAMPLE.split("SCENE 4")[0].split("SCENE 3")[0] + "SCENE 3 - EXT. UNDERGROUND CITY - NIGHT\nA huge city fades through haze.\n",
                        self.opts(max_attempts=2), ScriptedConsole(interactive=False), ScriptedLLM(stubborn))
        self.assertTrue(r["needs_review"])
        text = (self.ep(name="Episode 01 - The Six") / "README.md").read_text()
        self.assertIn("Needs your review", text)

    def test_a_model_that_never_submits_does_not_lose_the_episode(self):
        from seedance_agent.llm import Reply, ScriptedLLM

        def silent(system, messages, tools):
            if "submit_story_analysis" in {t["name"] for t in tools}:
                return good_model().fn(system, messages, tools)
            return Reply("I will think about it.")

        r = run_episode("SCENE 1 - INT. KITCHEN - NIGHT\nROXIE: Hi.\nDIESEL: Hello.\n", self.opts(), ScriptedConsole(interactive=False), ScriptedLLM(silent))
        self.assertEqual(r["needs_review"], ["S01"])
        ep = self.ep(name="Episode 01")
        txt = (ep / "Scene 01 - Kitchen" / "S01_single.txt").read_text()
        self.assertIn("“Hi.”", txt)
        self.assertIn("offline template draft", (ep / "README.md").read_text())

    def test_revise_a_clip(self):
        run_episode(SAMPLE, self.opts(), ScriptedConsole(interactive=False), good_model())
        notes = {}

        def reviser(system, messages, tools):
            if len(messages) == 1:
                from seedance_agent.llm import Reply, ToolCall
                ctx = messages[0]["content"]
                notes["asked"] = "revision_request" in ctx and "make it a wide" in ctx
                cur = json.loads(ctx.split("```json\n", 1)[1].rsplit("\n```", 1)[0])["current_prompt"]
                new = cur.replace("SHOT 1 — ESTABLISHING WIDE SHOT", "SHOT 1 — EXTREME WIDE SHOT")
                return Reply("", [ToolCall("r1", "submit_segment_prompt", {"segment_id": "S01a", "prompt": new, "shots": [], "brief": {},
                                                                          "carry_over": {}, "assumptions": ["Made shot 1 an extreme wide."]})])
            from seedance_agent.llm import Reply
            return Reply("done")

        from seedance_agent.llm import ScriptedLLM
        r = revise_segment(Options(output=self.out), ScriptedConsole(interactive=False), ScriptedLLM(reviser), "the six", 1, "s01a", "make it a wide")
        self.assertTrue(notes["asked"])
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["check_next"], ["S01b"])
        text = (self.ep() / "Scene 01 - Kitchen" / "S01a_generate.txt").read_text()
        self.assertIn("EXTREME WIDE SHOT", text)
        old = list((self.ep() / "_history").rglob("S01a_generate.txt"))
        self.assertEqual(len(old), 1)
        self.assertIn("ESTABLISHING WIDE SHOT", old[0].read_text())


class CameraLookup(unittest.TestCase):
    def test_recipe_and_flow_for_each_scene_type(self):
        from seedance_agent.tools import SCENE_TYPES
        for st in SCENE_TYPES:
            out = camera_lookup(st, "tense")
            self.assertIn("SCENE RECIPE", out, st)
            self.assertIn("SHOT FLOW", out, st)
            self.assertIn("Prompt fragment", out.split("SHOT FLOW")[0], st)
        self.assertIn("Unknown scene_type", camera_lookup("nonsense"))


if __name__ == "__main__":
    unittest.main()


class SloppyModelOutput(unittest.TestCase):
    def test_scene_numbers_as_strings_and_text_shots_are_tolerated(self):
        from seedance_agent.tools import AnalysisJob, SegmentJob
        a = AnalysisJob([1, 2])
        r = a.submit({"logline": "x", "spine": [{"act": "A", "scenes": ["1", "2"]}], "characters": ["not a dict"], "locations": [],
                      "scenes": [{"scene": "1", "scene_type": "dialogue"}, {"scene": "2"}]})
        self.assertTrue(r["accepted"], r)
        self.assertEqual([n["scene"] for n in a.analysis["scenes"]], [1, 2])
        self.assertEqual(a.analysis["spine"][0]["scenes"], [1, 2])
        self.assertEqual(a.analysis["characters"], [])
        seg = {"id": "S01", "mode": "single", "characters": [], "events": []}
        j = SegmentJob(seg, {"characters": {}}, {"clip_seconds": 15})
        out = j._normalise({"prompt": "x", "shots": ["wide shot", {"n": 1}], "brief": "text", "carry_over": None})
        self.assertEqual(out["shots"], [{"n": 1}])
        self.assertEqual(out["brief"]["purpose"], "")


class Seedance25Defaults(Base):
    def test_default_is_a_scene_per_generation_up_to_30_seconds(self):
        r = run_episode(SAMPLE, Options(output=self.out, movie="The Six", offline=True), ScriptedConsole(interactive=False), None)
        state = read_json(self.ep() / "episode.json")
        self.assertEqual(r["segments"], 5)  # one clip per scene
        self.assertEqual([s["mode"] for s in state["segments"]], ["single"] * 5)
        for s in state["segments"]:
            self.assertTrue(4 <= s["request_s"] <= 30, s["request_s"])
            self.assertEqual(s["request_s"], int(s["request_s"]))
        brief = (self.ep() / "Scene 01 - Kitchen" / "S01_brief.md").read_text()
        self.assertIn("## Seedance 2.5 settings", brief)
        self.assertIn("whole seconds from 4 to 30", brief)
        self.assertIn("Seedance 2.5 at 16:9, 1080p, audio on", (self.ep() / "README.md").read_text())

    def test_a_long_scene_is_split_beyond_the_chain_length(self):
        long_scene = "SCENE 1 - INT. HALL - DAY\n" + "\n".join(
            "ROXIE: Line %d of the long argument goes on and on." % i if i % 2 == 0 else "DIESEL: Reply %d is just as long as the line before it." % i
            for i in range(30))
        r = run_episode(long_scene, Options(output=self.out, movie="Long", offline=True), ScriptedConsole(interactive=False), None)
        state = read_json(Path(self.out) / "Long" / "Episode 01" / "episode.json")
        self.assertGreaterEqual(r["segments"], 2)
        self.assertEqual([s["mode"] for s in state["segments"]][:2], ["generate", "extend"])
        for s in state["segments"]:
            self.assertLessEqual(s["request_s"], 30)

    def test_new_chain_brief_warns_about_first_frame_inputs(self):
        from seedance_agent import render
        brief = render.generation_settings({"mode": "new-chain", "request_s": 12}, {"aspect_ratio": "16:9", "resolution": "1080p"})
        text = "\n".join(brief)
        self.assertIn("adaptive", text)
        self.assertIn("first-frame image together with reference images", text)
        self.assertIn("12 seconds", text)
        self.assertIn("40 seconds" if False else "4 to 30", text)


EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "ain-jalut-ep02"


class WorkedExample(Base):
    """Episode 02 of the worked example: a production-template script, prompts written outside the program, sheets, and the checks on all of it."""

    def run_example(self, **kw):
        text = (EXAMPLE / "script.txt").read_text(encoding="utf-8")
        opts = Options(output=self.out, prompts_file=str(EXAMPLE / "prompts.json"), wps=2.5, **kw)
        return run_episode(text, opts, ScriptedConsole(interactive=False), None), text

    def test_files_everything_under_movie_episode_scene(self):
        r, _ = self.run_example()
        ep = Path(r["path"])
        self.assertEqual(ep.relative_to(self.out).parts, ("Ain Jalut - The Spring of Goliath", "Episode 02 - The Slave Who Would Rule"))
        self.assertEqual((r["segments"], r["ok"]), (7, 7))
        self.assertEqual(sorted(p.name for p in ep.glob("Scene*")),
                         ["Scene 00 - Hook", "Scene 01 - The Market", "Scene 02 - The Dead Sultan", "Scene 03 - The Boy On The Throne", "Scene 04 - The Wall At Night"])
        self.assertEqual(len(list((ep / "characters").glob("@*.md"))), 7)
        self.assertEqual(len(list((ep / "locations").glob("@*.md"))), 5)
        state = read_json(ep / "episode.json")
        self.assertTrue(all(c["status"] == "ok" for c in state["sheets"]["characters"] + state["sheets"]["locations"]))

    def test_the_dialogue_is_the_script_word_for_word(self):
        import re
        r, text = self.run_example()
        ep = Path(r["path"])
        words = lambda parts: re.findall(r"[a-z0-9']+", " ".join(parts).lower())
        spoken = []
        for l in text.splitlines():
            m = re.match(r"^([A-Z][A-Z .'-]+):\s*(?:\([^)]*\)\s*)?(.+)$", l)
            if m and m.group(1) not in ("TEXT", "AIN JALUT") and not m.group(2).startswith(("THE SPRING", "Episode 03")):
                spoken.append(m.group(2))
        got = []
        for f in sorted(ep.glob("Scene*/S*.txt"), key=lambda p: p.name):
            body = f.read_text(encoding="utf-8")
            got += re.findall(r"“([^”]+)”", "SHOT 1" + body.split("SHOT 1", 1)[1])
        self.assertEqual(words(spoken), words(got))
        self.assertEqual(len(words(got)), 325)

    def test_scene_prompts_follow_the_studio_rules(self):
        r, _ = self.run_example()
        ep = Path(r["path"])
        for f in ep.glob("Scene*/S*.txt"):
            t = f.read_text(encoding="utf-8")
            self.assertIn("Visual Style: 2D anime", t, f.name)
            self.assertIn("[Negative: chinese language, mandarin, chinese speech, asian accent]", t, f.name)
            self.assertIn("[System: Language: English] [Audio: English Speech]", t, f.name)
            self.assertNotIn("@ TAG", t, f.name)
            self.assertRegex(t, r"SHOT 1 \(00:00-00:\d\d\)", f.name)
        market = (ep / "Scene 01 - The Market" / "S01_single.txt").read_text(encoding="utf-8")
        self.assertIn("DEALER: slave dealer, man in his 40s", market)          # described in full: no image
        self.assertNotIn("@Dealer", market)

    def test_plan_only_writes_the_plan_and_no_prompts(self):
        text = (EXAMPLE / "script.txt").read_text(encoding="utf-8")
        r = run_episode(text, Options(output=self.out, plan_only=True, wps=2.5), ScriptedConsole(interactive=False), None)
        ep = Path(r["path"])
        self.assertEqual((r["segments"], r["ok"]), (7, 0))
        self.assertTrue((ep / "plan.html").exists())
        self.assertFalse(list(ep.glob("Scene*/S*.txt")))

    def test_running_again_keeps_the_earlier_files_in_history(self):
        self.run_example()
        r, _ = self.run_example()
        self.assertTrue(list((Path(r["path"]) / "_history").glob("*")))
