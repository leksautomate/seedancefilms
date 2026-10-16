import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT  # noqa: F401  (sets sys.path)
from seedance_agent.console import ScriptedConsole
from seedance_agent.intake import NeedInput, parse_header, resolve
from seedance_agent.library import EpisodeFolder, Library, scene_folder_name


class Header(unittest.TestCase):
    def test_movie_episode_and_title(self):
        h = parse_header('MOVIE: Wolf & Girl\nEPISODE 3 - "The Six"\n\nSCENE 1 - INT. KITCHEN')
        self.assertEqual((h.movie, h.number, h.title), ("Wolf & Girl", 3, "The Six"))

    def test_title_only(self):
        h = parse_header('EPISODE 1 - "THE SIX"\nSCENE 1 - INT. KITCHEN')
        self.assertEqual((h.movie, h.number, h.title), (None, 1, "THE SIX"))

    def test_nothing(self):
        h = parse_header("SCENE 1 - INT. KITCHEN\nROXIE: Hi.")
        self.assertEqual((h.movie, h.number, h.title), (None, None, None))

    def test_header_after_scene_start_is_ignored(self):
        h = parse_header("SCENE 1 - INT. KITCHEN\nMOVIE: Late")
        self.assertIsNone(h.movie)


class Names(unittest.TestCase):
    def test_scene_folder(self):
        self.assertEqual(scene_folder_name(1, "SCENE 1 - INT. KITCHEN - NIGHT", "kitchen"), "Scene 01 - Kitchen")
        self.assertEqual(scene_folder_name(12, "(no heading)", ""), "Scene 12")


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lib = Library(Path(self.tmp.name) / "output")

    def tearDown(self):
        self.tmp.cleanup()

    def test_asks_for_the_movie_when_missing(self):
        con = ScriptedConsole(["Wolf and Girl", ""])
        r = resolve("SCENE 1 - INT. KITCHEN\nROXIE: Hi.\n", self.lib, con)
        self.assertEqual(r.movie, "Wolf and Girl")
        self.assertTrue(r.is_new_movie)
        self.assertEqual(r.number, 1)
        self.assertIn("movie", con.asked[0].lower())

    def test_non_interactive_without_movie_fails(self):
        with self.assertRaises(NeedInput):
            resolve("SCENE 1 - INT. KITCHEN\n", self.lib, ScriptedConsole(interactive=False))

    def test_movie_from_script_header(self):
        r = resolve('MOVIE: The Six\nEPISODE 2 - "Red Light"\nSCENE 1 - INT. KITCHEN\n', self.lib, ScriptedConsole(interactive=False))
        self.assertEqual((r.movie, r.number, r.title), ("The Six", 2, "Red Light"))

    def test_existing_movie_is_matched_ignoring_case_and_gets_next_episode(self):
        m = self.lib.open_movie("The Six")
        m.save()
        (m.dir / "Episode 01 - Pilot").mkdir(parents=True)
        r = resolve("SCENE 1 - INT. KITCHEN\n", self.lib, ScriptedConsole(interactive=False), movie="the six")
        self.assertEqual(r.movie, "The Six")
        self.assertFalse(r.is_new_movie)
        self.assertEqual(r.number, 2)

    def test_pick_existing_movie_by_number(self):
        self.lib.open_movie("Alpha").save()
        self.lib.open_movie("Beta").save()
        con = ScriptedConsole(["2", ""])
        r = resolve("SCENE 1 - INT. KITCHEN\n", self.lib, con)
        self.assertEqual(r.movie, "Beta")

    def test_new_episode_flag(self):
        m = self.lib.open_movie("The Six")
        m.save()
        (m.dir / "Episode 01 - Pilot").mkdir(parents=True)
        r = resolve("EPISODE 1\nSCENE 1 - INT. KITCHEN\n", self.lib, ScriptedConsole(interactive=False), movie="The Six", new_episode=True)
        self.assertEqual(r.number, 2)


class Versioning(unittest.TestCase):
    def test_old_versions_are_kept_and_same_run_rewrites_do_not_clutter(self):
        with tempfile.TemporaryDirectory() as d:
            ep = Path(d) / "Episode 01"
            f = EpisodeFolder(ep)
            f.write("a.txt", "one")
            f.write("a.txt", "two")  # same run: overwritten, nothing archived
            self.assertFalse((ep / "_history").exists())
            f2 = EpisodeFolder(ep)  # a later run
            f2.write("a.txt", "three")
            hist = list((ep / "_history").rglob("a.txt"))
            self.assertEqual(len(hist), 1)
            self.assertEqual(hist[0].read_text(), "two")
            self.assertEqual((ep / "a.txt").read_text(), "three")


if __name__ == "__main__":
    unittest.main()
