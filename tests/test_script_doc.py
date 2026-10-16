import unittest
from pathlib import Path

from tests.helpers import SAMPLE
from seedance_agent import script_doc

AIN = (Path(__file__).resolve().parent.parent / "examples" / "ain-jalut-ep02" / "script.txt").read_text(encoding="utf-8")


class Parse(unittest.TestCase):
    def setUp(self):
        self.doc = script_doc.parse(AIN)

    def test_header(self):
        d = self.doc
        self.assertEqual(d.movie, "AIN JALUT: THE SPRING OF GOLIATH")
        self.assertEqual(d.episode_number, 2)
        self.assertEqual(d.episode_title, "The Slave Who Would Rule")
        self.assertEqual(d.runtime_s, 180)

    def test_scenes_follow_the_runtime_map(self):
        d = self.doc
        self.assertEqual([s.number for s in d.scenes], [0, 1, 2, 3, 4])
        self.assertEqual([s.title for s in d.scenes], ["Hook", "The Market", "The Dead Sultan", "The Boy On The Throne", "The Wall At Night"])
        self.assertEqual([s.planned_s for s in d.scenes], [18, 33, 40, 55, 30])
        self.assertEqual([s.intext for s in d.scenes], ["INT.", "EXT.", "INT.", "INT.", "EXT."])

    def test_dialogue_lines_are_kept_whole(self):
        lines = sum(len(s.lines) for s in self.doc.scenes)
        self.assertGreaterEqual(lines, 36)

    def test_characters_and_locations_come_from_the_lists(self):
        names = [c["name"] if isinstance(c, dict) else c for c in self.doc.characters]
        self.assertIn("Shajar al-Durr", names)
        self.assertIn("Slave Dealer", names)
        self.assertEqual(len(self.doc.locations), 5)
        self.assertEqual(self.doc.locations[0]["name"], "Qutuz's tent, Salihiyya camp")

    def test_on_screen_text_and_the_opening_are_not_scenes(self):
        self.assertIn("DREAMINA ORIGINALS OPENING", self.doc.opening)
        self.assertEqual(self.doc.scenes[0].overlays, ["Damascus. Many years earlier."])
        self.assertEqual(self.doc.scenes[2].overlays, ["Cairo Citadel, 1257."])
        self.assertEqual(self.doc.scenes[0].on_screen, ["Qutuz (adult)", "Elder Emir"])
        self.assertIn("Episode 03", self.doc.end_card)

    def test_normalized_text_is_one_block_per_scene(self):
        n = self.doc.normalized
        self.assertEqual(n.count("SCENE "), 5)
        self.assertIn("SCENE 1 - EXT. DAMASCUS SLAVE MARKET - MIDDAY", n)
        self.assertNotIn("Characters on screen", n)

    def test_other_scripts_are_not_treated_as_the_template(self):
        self.assertIsNone(script_doc.parse(SAMPLE))

    def test_default_tag_for_a_place(self):
        self.assertEqual(script_doc.tag_for_place("Qutuz's tent, Salihiyya camp"), "@ TAG QUTUZ TENT")


if __name__ == "__main__":
    unittest.main()
