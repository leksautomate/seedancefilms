import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import SAMPLE, good_model, json_after
from seedance_agent import sheets
from seedance_agent.console import ScriptedConsole
from seedance_agent.llm import Reply, ScriptedLLM, ToolCall
from seedance_agent.pipeline import Options, run_episode

AIN = (Path(__file__).resolve().parent.parent / "examples" / "ain-jalut-ep02" / "script.txt").read_text(encoding="utf-8")
PALETTE = [{"label": n, "hex": h} for n, h in (("Skin", "#C79A6B"), ("Hair", "#1B1512"), ("Coat", "#7A1F1F"), ("Metal", "#8A929B"))]
VOICE = {"language_accent": "English, neutral (proposed)", "gender_age": "Male, 40s (proposed)", "persona": "Stern guardian", "emotion": "Controlled, grave",
         "delivery": "Low and unhurried.",
         "preview_text": "Let them. The Mongols never ask who sits on a throne. They ask if it stands. A boy cannot lift a sword."}


def char(name="Qutuz (adult)", tag="@Qutuz", **kw):
    e = {k: "plain text for %s" % k for k in sheets.CHAR_REQUIRED}
    e.update(name=name, tag=tag, palette=PALETTE, notes=["rolled sleeves"], proposed=["age"], close_up="His face by torchlight")
    e.update(kw)
    return e


def loc(name="Citadel wall", tag="@CitadelWall", **kw):
    e = {k: "plain text for %s" % k for k in sheets.LOC_REQUIRED}
    e.update(name=name, tag=tag, palette=PALETTE, notes=["wind"], proposed=["scale"], setting_type="exterior")
    e.update(kw)
    return e


class Render(unittest.TestCase):
    def test_pascal_tags(self):
        self.assertEqual(sheets.pascal("Qutuz"), "@Qutuz")
        self.assertEqual(sheets.pascal("Shajar al-Durr"), "@ShajarAlDurr")
        self.assertEqual(sheets.pascal("Cairo Citadel royal bath chamber"), "@CairoCitadelRoyalBathChamber")

    def test_character_prompt_follows_the_template(self):
        p = sheets.render_character_prompt(char(), "2D anime")
        self.assertTrue(p.startswith("Create a polished 16:9 landscape continuity sheet focused exclusively on the character, rendered in 2D anime:"))
        for n in range(1, 9):
            self.assertIn("\n%d. " % n, p)
        self.assertIn("#C79A6B", p)
        self.assertIn("plain solid white studio background", p)
        self.assertIn("NOTES PANEL", p)
        self.assertIn("CLOSE-UP POSE", p)
        self.assertIn("stylized materials", p)
        self.assertNotIn("realistic materials", p)
        self.assertNotIn("..", p)

    def test_photoreal_style_keeps_realistic_materials(self):
        self.assertIn("realistic materials", sheets.render_character_prompt(char(), "Photorealistic cinematic"))

    def test_location_prompt_follows_the_template(self):
        p = sheets.render_location_prompt(loc(), "2D anime")
        self.assertIn("focused exclusively on the location, rendered in 2D anime:", p)
        for n in range(1, 9):
            self.assertIn("\n%d. " % n, p)
        self.assertIn("Do not include people, characters, vehicles", p)
        self.assertNotIn("..", p)

    def test_file_has_the_tag_first_and_the_voice_prompt_last(self):
        e = char(voice=VOICE)
        text = sheets.character_file(e, "2D anime")
        self.assertEqual(text.splitlines()[0], "@Qutuz")
        self.assertIn("\n\nVOICE DESIGN PROMPT: English, neutral (proposed). Male, 40s (proposed). Studio quality. Persona: Stern guardian.", text)
        self.assertLess(text.index("Do not include props"), text.index("VOICE DESIGN PROMPT"))
        self.assertNotIn("VOICE DESIGN", sheets.character_file(char(), "2D anime"))


class Lint(unittest.TestCase):
    def check(self, e, **kw):
        kw.setdefault("others", [])
        kw.setdefault("speech_lines", [])
        kw.setdefault("recurring", False)
        return sheets.lint_character(e, sheets.render_character_prompt(e, "2D anime"), "2D anime", **kw)

    def test_a_complete_sheet_passes(self):
        self.assertEqual(self.check(char())["errors"], [])

    def test_missing_fields_and_bad_tags(self):
        e = char()
        e["lock"] = ""
        e["tag"] = "@ Qutuz"
        errs = " ".join(self.check(e)["errors"])
        self.assertIn("Missing field(s): lock", errs)
        self.assertIn("PascalCase", errs)

    def test_palette_needs_real_hex_codes(self):
        e = char(palette=[{"label": "Skin", "hex": "tan"}] * 4)
        self.assertIn("HEX", " ".join(self.check(e)["errors"]))

    def test_placeholders_are_rejected(self):
        e = char(lock="{{lock}}")
        self.assertIn("placeholder", " ".join(self.check(e)["errors"]))

    def test_one_character_per_prompt(self):
        e = char(role="Stands next to Shajar all day")
        errs = self.check(e, others=[{"name": "Shajar al-Durr"}])["errors"]
        self.assertTrue(any("One character per prompt" in x and "Shajar" in x for x in errs), errs)

    def test_a_title_word_is_not_another_character(self):
        e = char(role="An emir who becomes sultan")
        self.assertEqual(self.check(e, others=[{"name": "Elder Emir"}])["errors"], [])

    def test_voice_only_for_recurring_characters(self):
        self.assertTrue(any("single scene" in x for x in self.check(char(voice=VOICE), recurring=False)["errors"]))
        self.assertTrue(any("needs a voice design" in x for x in self.check(char(), recurring=True)["errors"]))

    def test_voice_rules(self):
        lines = ["Let them. The Mongols never ask who sits on a throne. They ask if it stands.", "A boy cannot lift a sword."]
        ok = self.check(char(voice=VOICE), recurring=True, speech_lines=lines)
        self.assertEqual(ok["errors"], [])
        bad = dict(VOICE, delivery="Add reverb and an echo.")
        self.assertTrue(any("effect word" in x for x in self.check(char(voice=bad), recurring=True, speech_lines=lines)["errors"]))
        bad = dict(VOICE, language_accent="English with an accent")
        self.assertTrue(any("slight" in x for x in self.check(char(voice=bad), recurring=True, speech_lines=lines)["errors"]))
        bad = dict(VOICE, preview_text="Too short.")
        self.assertTrue(any("100 characters" in x for x in self.check(char(voice=bad), recurring=True, speech_lines=lines)["errors"]))
        bad = dict(VOICE, preview_text=VOICE["preview_text"] + " And I made this one up myself, word for word.")
        self.assertTrue(any("word for word" in x for x in self.check(char(voice=bad), recurring=True, speech_lines=lines)["errors"]))

    def test_a_location_has_no_people(self):
        e = loc(role="Where Qutuz looks north")
        errs = sheets.lint_location(e, sheets.render_location_prompt(e, "2D anime"), "2D anime", [{"name": "Qutuz (adult)"}])["errors"]
        self.assertTrue(any("no people" in x for x in errs), errs)
        ok = loc()
        self.assertEqual(sheets.lint_location(ok, sheets.render_location_prompt(ok, "2D anime"), "2D anime", [{"name": "Qutuz (adult)"}])["errors"], [])


class SheetJobGate(unittest.TestCase):
    def test_three_bad_submissions_end_as_needs_review(self):
        job = sheets.SheetJob("character", "2D anime", recurring=False)
        for _ in range(3):
            r = job.submit(char(lock=""))
        self.assertTrue(r["accepted"])
        self.assertEqual(job.accepted["status"], "needs-review")

    def test_a_good_submission_is_accepted_at_once(self):
        job = sheets.SheetJob("location", "2D anime", characters=[{"name": "Qutuz"}])
        r = job.submit(loc())
        self.assertEqual((r["accepted"], r["status"]), (True, "ok"))


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = str(Path(self.tmp.name) / "output")

    def tearDown(self):
        self.tmp.cleanup()

    def spec(self, data):
        p = Path(self.tmp.name) / "spec.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return str(p)

    def test_sheets_only_from_a_spec(self):
        data = {"sheets": {
            "characters": [char(speakers=["QUTUZ"], lead=True, voice=VOICE), char("Elder Emir", "@ElderEmir", speakers=["ELDER EMIR"]),
                           char("Qutuz (child)", "@QutuzChild", speakers=["YOUNG QUTUZ"])],
            "locations": [loc("Citadel wall at night", "@CitadelWall", match="Citadel wall")],
            "extras": [{"name": "DEALER", "look": "man in his 40s, stocky"}]}}
        r = run_episode(AIN, Options(output=self.out, prompts_file=self.spec(data), sheets="only", visual_style="2D anime", wps=2.5),
                        ScriptedConsole(interactive=False), None)
        ep = Path(r["path"])
        self.assertEqual(ep.parent.name, "Ain Jalut - The Spring of Goliath")
        self.assertTrue((ep / "characters" / "@Qutuz.md").exists())
        self.assertTrue((ep / "characters" / "@ElderEmir.md").exists())
        self.assertTrue((ep / "locations" / "@CitadelWall.md").exists())
        self.assertTrue((ep / "images" / "characters").is_dir())
        self.assertEqual([p.name for p in (ep / "images" / "characters").iterdir() if not p.name.startswith(".")], [])
        self.assertTrue((ep / "characters-and-locations.md").exists())
        self.assertIn("VOICE DESIGN PROMPT", (ep / "characters" / "@Qutuz.md").read_text())
        self.assertNotIn("VOICE DESIGN PROMPT", (ep / "characters" / "@QutuzChild.md").read_text())  # speaks in one scene only
        self.assertIn("DEALER", (ep / "characters-and-locations.md").read_text())
        self.assertFalse(list(ep.glob("Scene*")))

    def test_the_recurring_rule_uses_the_scenes_of_the_script(self):
        data = {"sheets": {"characters": [char("Elder Emir", "@ElderEmir", speakers=["ELDER EMIR"])], "locations": []}}  # in scenes 0, 3, 4 but no voice given
        r = run_episode(AIN, Options(output=self.out, prompts_file=self.spec(data), sheets="only", visual_style="2D anime", wps=2.5),
                        ScriptedConsole(interactive=False), None)
        sh = json.loads((Path(r["path"]) / "episode.json").read_text())["sheets"]
        self.assertEqual(sh["characters"][0]["status"], "needs-review")
        self.assertTrue(any("voice design" in x for x in sh["characters"][0]["errors"]))

    def test_no_style_means_no_sheets(self):
        data = {"sheets": {"characters": [char(speakers=["QUTUZ"])], "locations": []}}
        console = ScriptedConsole(interactive=False)
        r = run_episode(AIN, Options(output=self.out, prompts_file=self.spec(data), sheets="only", wps=2.5), console, None)
        self.assertFalse((Path(r["path"]) / "characters").exists())

    def test_skip_leaves_the_folders_out(self):
        r = run_episode(AIN, Options(output=self.out, offline=True, sheets="skip", visual_style="2D anime", wps=2.5), ScriptedConsole(interactive=False), None)
        self.assertFalse((Path(r["path"]) / "characters").exists())

    def test_the_model_writes_the_sheets_through_the_gate(self):
        base = good_model()
        seen = []

        def fn(system, messages, tools):
            names = {t["name"] for t in tools}
            if "submit_sheet" in names:
                ctx = json_after(messages[0]["content"], "## The entry")
                seen.append(ctx["kind"])
                entry = ctx["entry"]
                if ctx["kind"] == "character":
                    e = char(entry["name"].title(), entry["tag"], speakers=entry.get("speakers") or [entry["name"].upper()])
                    if ctx["needs_voice_design_prompt"]:
                        e["voice"] = dict(VOICE, preview_text=" ".join(ctx["its_own_script_lines"])[:400])
                else:
                    e = loc(entry["name"], entry["tag"])
                if len(messages) == 1:
                    return Reply("", [ToolCall("s1", "submit_sheet", e)])
                return Reply("Done.")
            return base.fn(system, messages, tools)

        llm = ScriptedLLM(fn)
        r = run_episode(SAMPLE, Options(output=self.out, movie="The Six", visual_style="2D anime", sheets="auto", clip=15.0, chain=30.0), ScriptedConsole(interactive=False), llm)
        ep = Path(r["path"])
        self.assertIn("character", seen)
        self.assertIn("location", seen)
        self.assertTrue(list((ep / "characters").glob("@*.md")))
        self.assertTrue(list((ep / "locations").glob("@*.md")))
        self.assertEqual(r["ok"], r["segments"])


if __name__ == "__main__":
    unittest.main()
