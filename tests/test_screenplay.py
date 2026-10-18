import tempfile
import unittest
from pathlib import Path

from tests.helpers import SAMPLE, ROOT
from seedance_agent import screenplay
from seedance_agent.workbench import Workbench

KALIO = (ROOT / "examples" / "arrogant-husband-ep01" / "script.txt").read_text(encoding="utf-8")
MOVIE = "Arrogant Husband Cast Out His Loyal Wife, Only to Discover Who Signed His Paychecks"


class Normalize(unittest.TestCase):
    def test_cue_note_and_line_become_one_line(self):
        out = screenplay.normalize("RICHARD\n(laughing, loud)\n\n\nLook at her! Who asked you?\n\nESTHER\nIn this rain? At night?\n")
        self.assertIn("RICHARD: (laughing, loud) Look at her! Who asked you?", out)
        self.assertIn("ESTHER: In this rain? At night?", out)

    def test_continued_marker_is_dropped_and_lines_are_joined(self):
        out = screenplay.normalize("RICHARD (CONT'D)\n(sneering)\nAnd take that trinket.\nSeven years.\n")
        self.assertEqual(out.strip(), "RICHARD: (sneering) And take that trinket. Seven years.")

    def test_headings_transitions_and_action_are_left_alone(self):
        src = "**INT. HOUSE. NIGHT**\n\nRain.\n\nCUT TO BLACK.\n\nFADE OUT\nThe end.\n"
        out = screenplay.normalize(src)
        self.assertIn("INT. HOUSE. NIGHT", out)
        self.assertNotIn("**", out)
        self.assertIn("CUT TO BLACK.", out)
        self.assertNotIn("FADE OUT:", out)

    def test_colon_scripts_are_unchanged(self):
        self.assertEqual(screenplay.normalize(SAMPLE), SAMPLE.replace("**", ""))
        self.assertNotIn(": (", screenplay.normalize("WOLF: No.\nGIRL: Yes.\n"))
        self.assertEqual(screenplay.normalize("WOLF: No.\nGIRL: Yes.\n"), "WOLF: No.\nGIRL: Yes.\n")


class ScreenplayEpisode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wb = Workbench(str(Path(self.tmp.name) / "output"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_dialogue_is_the_spoken_lines_and_notes_are_delivery(self):
        r = self.wb.call("start_episode", {"script": KALIO, "movie": MOVIE, "episode": 1, "visual_style": "3D animated", "language_lock": True, "wps": 2.8})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["movie"], MOVIE)                       # the whole title, not cut at 60 characters
        self.assertEqual(sorted(r["speakers_and_their_scenes"]), ["ESTHER", "RICHARD", "STEPHANIE"])
        dialogue = [e for c in r["clips"] for e in c["events"] if e["kind"] == "dialogue"]
        self.assertEqual(len(dialogue), 15)   # Richard 8, Esther 6, Stephanie 1
        self.assertFalse([e for e in dialogue if e["text"].startswith("(")])
        self.assertEqual(dialogue[0]["text"][:20], "Look at her! A prima")
        self.assertEqual(dialogue[0]["how"], "laughing, loud, glass raised")
        spoken = " ".join(e["text"] for e in dialogue)
        for line in ("In this rain? At night?", "My father's pen is not a trinket.", "See whose name carries it."):
            self.assertIn(line, spoken)
        self.assertEqual([c["id"] for c in r["clips"]], ["S01a", "S01b", "S01c", "S01d"])


if __name__ == "__main__":
    unittest.main()
