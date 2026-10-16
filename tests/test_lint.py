import unittest

from tests.helpers import SAMPLE
from seedance_agent import lint, offline
from seedance_agent import skills_bridge as sb

SETTINGS = {"clip_seconds": 15}


def bible_for(seg):
    return {"characters": {n: {"tag": "@ TAG %s" % n, "voice": "A voice for %s." % n} for n in seg["characters"]}, "locations": {}}


class Base(unittest.TestCase):
    def setUp(self):
        self.segs = sb.segment(SAMPLE, clip=15.0, chain=30.0)  # the 15 second layout
        self.seg = self.segs[0]
        self.bible = bible_for(self.seg)
        self.draft = offline.draft(self.seg, self.bible, SETTINGS, None)["prompt"]

    def run_lint(self, prompt, seg=None, prev=None):
        seg = seg or self.seg
        return lint.lint(prompt, seg, bible_for(seg), SETTINGS, "full", prev)



class Lint(Base):
    def test_clean_prompt_passes(self):
        r = self.run_lint(self.draft)
        self.assertEqual(r["errors"], [], r["errors"])

    def test_changed_dialogue_is_rejected(self):
        bad = self.draft.replace("No.", "Nope.")
        r = self.run_lint(bad)
        self.assertTrue(any("Dialogue must match" in e for e in r["errors"]), r["errors"])

    def test_dropped_dialogue_is_rejected(self):
        bad = self.draft.replace("“BABE!”", "")
        self.assertTrue(any("Dialogue must match" in e for e in self.run_lint(bad)["errors"]))

    def test_added_dialogue_is_rejected(self):
        bad = self.draft.replace("HARD CUT.", "HARD CUT.\n\nWOLF says:\n“Extra line here.”", 1)
        self.assertTrue(any("Dialogue must match" in e for e in self.run_lint(bad)["errors"]))

    def test_split_line_across_shots_is_allowed(self):
        seg = {"id": "X", "mode": "single", "characters": ["GIRL"], "request_s": 15,
               "events": [{"kind": "dialogue", "speaker": "GIRL", "text": "You thought what?", "words": 3, "seconds": 1}]}
        d = offline.draft(seg, bible_for(seg), SETTINGS, None)["prompt"]
        d = d.replace("“You thought what?”", "“You thought—”\n\nHARD CUT.\n\nSHOT 2 — CLOSE-UP — EYE LEVEL\n\n“...what?”")
        self.assertEqual(lint.lint(d, seg, bible_for(seg), SETTINGS, "full")["errors"], [])

    def test_missing_hard_cut_rule(self):
        bad = self.draft.replace("Use ONLY hard cuts between shots.", "")
        self.assertTrue(any("hard cuts" in e for e in self.run_lint(bad)["errors"]))

    def test_missing_no_music(self):
        bad = self.draft.replace("NO music.", "")
        self.assertTrue(any("NO music" in e for e in self.run_lint(bad)["errors"]))

    def test_missing_ending(self):
        bad = self.draft.rstrip().rsplit("\n", 1)[0] + "\n\nThe end of the clip."
        self.assertTrue(any("End the prompt" in e for e in self.run_lint(bad)["errors"]))

    def test_placeholder(self):
        bad = self.draft.replace("Kitchen", "<location name>", 1)
        self.assertTrue(any("Placeholder" in e for e in self.run_lint(bad)["errors"]))

    def test_shot_numbers_must_be_sequential(self):
        bad = self.draft.replace("SHOT 2", "SHOT 5", 1)
        self.assertTrue(any("without gaps" in e for e in self.run_lint(bad)["errors"]))

    def test_missing_voice_block(self):
        bad = self.draft.replace("GIRL'S VOICE:", "GIRL:")
        self.assertTrue(any("voice block" in e for e in self.run_lint(bad)["errors"]))

    def test_missing_tag(self):
        bad = self.draft.replace("@ TAG GIRL", "GIRL")
        self.assertTrue(any("tag" in e and "GIRL" in e for e in self.run_lint(bad)["errors"]))

    def test_extension_must_quote_previous_last_line(self):
        ext = self.segs[1]
        prev = {"last_line": "Are you SURE? They feel so tight...", "last_speaker": "GIRL"}
        good = offline.draft(ext, bible_for(ext), SETTINGS, prev)["prompt"]
        self.assertEqual(self.run_lint(good, ext, prev)["errors"], [])
        bad = good.replace("Are you SURE? They feel so tight...", "something else entirely")
        self.assertTrue(any("quote the previous clip" in e for e in self.run_lint(bad, ext, prev)["errors"]))

    def test_extension_needs_no_tags(self):
        ext = self.segs[1]
        prev = {"last_line": "Are you SURE? They feel so tight...", "last_speaker": "GIRL"}
        good = offline.draft(ext, bible_for(ext), SETTINGS, prev)["prompt"]
        self.assertNotIn("@ TAG GIRL", good)
        self.assertEqual(self.run_lint(good, ext, prev)["errors"], [])

    def test_too_long_is_an_error(self):
        many = {"id": "L", "mode": "single", "characters": ["GIRL"], "request_s": 15,
                "events": [{"kind": "dialogue", "speaker": "GIRL", "text": " ".join(["word"] * 12) + "?", "words": 12, "seconds": 4}] * 6}
        d = offline.draft(many, bible_for(many), SETTINGS, None)["prompt"]
        r = lint.lint(d, many, bible_for(many), SETTINGS, "full")
        self.assertTrue(any("Estimated" in e and "limit" in e for e in r["errors"]), r["errors"])

class StudioRules(Base):
    """The studio's Seedance rules: @Name tags, the English-language lock, one Visual Style line, extras described in full."""

    LOCK = "[Negative: chinese language, mandarin, chinese speech, asian accent]\n[System: Language: English] [Audio: English Speech]"

    def locked(self):
        return {"clip_seconds": 15, "language_lock": True, "visual_style": "2D anime"}

    def run_with(self, prompt, settings, bible=None):
        return lint.lint(prompt, self.seg, bible or self.bible, settings, "full", None)

    def test_language_lock_lines_are_required(self):
        r = self.run_with(self.draft, self.locked())
        text = " ".join(r["errors"])
        self.assertIn("[Negative: chinese language", text)
        self.assertIn("[System: Language: English]", text)
        self.assertIn("Visual Style", text)

    def test_language_lock_passes_with_the_lines(self):
        d = self.draft.replace("\n\n", "\n\nVisual Style: 2D anime.\n" + self.LOCK + "\n\n", 1)
        r = self.run_with(d, self.locked())
        self.assertEqual([e for e in r["errors"] if "Missing" in e or "Visual Style" in e], [])

    def test_no_lock_no_extra_rules(self):
        r = self.run_with(self.draft, {"clip_seconds": 15})
        self.assertEqual(r["errors"], [])

    def test_a_tag_must_match_as_a_whole_word(self):
        bible = {"characters": {n: {"tag": "@Ali", "voice": "v"} for n in self.seg["characters"][:1]}, "locations": {}}
        d = self.draft.replace("@ TAG", "@AliBaba")
        warn_or_err = " ".join(self.run_with(d, {"clip_seconds": 15}, bible)["errors"] + self.run_with(d, {"clip_seconds": 15}, bible)["warnings"])
        self.assertIn("@Ali", warn_or_err)

    def test_a_character_without_an_image_must_be_described(self):
        name = self.seg["characters"][0]
        bible = {"characters": {n: {"tag": "@ TAG %s" % n, "voice": "v"} for n in self.seg["characters"]}, "locations": {}}
        bible["characters"][name] = {"no_image": True, "tag": "", "look": "man in his 40s, stocky, dark beard", "voice": "v"}
        r = self.run_with(self.draft, {"clip_seconds": 15}, bible)
        self.assertTrue(any("no reference image" in w for w in r["warnings"]), r["warnings"])
        d = self.draft.replace(name, "%s (man in his 40s, stocky, dark beard)" % name, 1)
        r = self.run_with(d, {"clip_seconds": 15}, bible)
        self.assertFalse(any("no reference image" in w for w in r["warnings"]), r["warnings"])

    def test_shot_timestamps_are_accepted(self):
        d = self.draft.replace("SHOT 1 \u2014", "SHOT 1 (00:00-00:03) \u2014", 1)
        self.assertEqual(self.run_lint(d)["errors"], [])



if __name__ == "__main__":
    unittest.main()
