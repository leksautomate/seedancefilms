import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from tests.helpers import SAMPLE
from seedance_agent import cli
from seedance_agent.console import Console


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


class Interactive(unittest.TestCase):
    def test_paste_then_asked_for_the_movie_name(self):
        """The real flow: run with no arguments, paste the script, finish with END, answer the movie question."""
        script = SAMPLE.replace('EPISODE 1 - "THE SIX"\n', "")  # no movie, no title in the script
        typed = script + "\nEND\nMy Wolf Movie\nPilot\n"
        with tempfile.TemporaryDirectory() as d:
            err = io.StringIO()
            with mock.patch.object(sys, "stdin", FakeTTY(typed)), redirect_stderr(err):
                code = cli.main(["--offline", "--output", d])
            self.assertEqual(code, 0, err.getvalue())
            ep = Path(d) / "My Wolf Movie" / "Episode 01 - Pilot"
            self.assertTrue((ep / "prompts-all.md").exists())
            self.assertIn("name of the movie", err.getvalue())
            self.assertIn("Saved in:", err.getvalue())

    def test_piped_script_without_a_movie_explains_what_to_do(self):
        with tempfile.TemporaryDirectory() as d:
            err = io.StringIO()
            with mock.patch.object(sys, "stdin", io.StringIO(SAMPLE)), redirect_stderr(err):
                code = cli.main(["--offline", "--output", d])
            self.assertEqual(code, 2)
            self.assertIn("--movie", err.getvalue())
            self.assertFalse(any(Path(d).iterdir()))

    def test_piped_script_with_a_movie(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(sys, "stdin", io.StringIO(SAMPLE)), redirect_stderr(io.StringIO()):
                code = cli.main(["--offline", "--output", d, "--movie", "Piped Movie"])
            self.assertEqual(code, 0)
            self.assertTrue((Path(d) / "Piped Movie" / "movie.json").exists())

    def test_no_model_configured_says_how_to_fix_it(self):
        err = io.StringIO()
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(sys, "stdin", io.StringIO(SAMPLE)), redirect_stderr(err):
            code = cli.main(["--movie", "X", "--output", tempfile.gettempdir() + "/never_written"])
        self.assertEqual(code, 2)
        self.assertIn("ANTHROPIC_API_KEY", err.getvalue())
        self.assertIn("--offline", err.getvalue())

    def test_list(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(sys, "stdin", io.StringIO(SAMPLE)), redirect_stderr(io.StringIO()):
                cli.main(["--offline", "--output", d, "--movie", "Listed"])
            out = io.StringIO()
            with redirect_stdout(out):
                cli.main(["list", "--output", d])
            self.assertIn("Listed", out.getvalue())
            self.assertIn("Episode 01", out.getvalue())


class ConsoleTests(unittest.TestCase):
    def test_read_script_stops_at_END(self):
        c = Console(inp=io.StringIO("line one\nline two\nEND\nignored\n"), out=io.StringIO())
        self.assertEqual(c.read_script(), "line one\nline two\n")


if __name__ == "__main__":
    unittest.main()
