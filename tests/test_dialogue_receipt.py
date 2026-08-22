"""Red-gate tests for ``tools/dialogue_receipt.py``.

Every check here is proven falsifiable against a synthetic transcript, in the
same spirit as ``test_audition_receipt.py``: a check that cannot go red is
theater. Two of these fixtures are transcriptions of REAL defects that reached
the Director on 2026-08-22 — the phantom fourth line and the mid-line pause —
so the suite carries the evidence that the tool would have caught them.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import dialogue_receipt  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENE_PATH = os.path.join(REPO_ROOT, "docs", "scenes", "night-street.json")


def words(*spans):
    """Build a word list from (text, start, end, speaker) tuples."""
    return [
        {"text": t, "start": s, "end": e, "speaker_id": spk, "type": "word"}
        for t, s, e, spk in spans
    ]


def say(text, start, speaker, rate=0.30, gap=0.05):
    """Lay a phrase out as evenly spaced words. Returns (spans, end_time)."""
    out = []
    t = start
    for token in text.split():
        out.append((token, round(t, 3), round(t + rate, 3), speaker))
        t += rate + gap
    return out, round(t - gap, 3)


SCENE = {
    "clip_duration_s": 10.062,
    "max_gap_within_line_s": 0.5,
    "lines": [
        {"speaker": "VOICE", "text": "Hey, how's it going?"},
        {"speaker": "MAC", "text": "Not bad. Can't complain.", "max_gap_s": 0.15},
        {"speaker": "VOICE", "text": "Good to hear, good to hear."},
    ],
}


def clean_transcript():
    a, end_a = say("Hey how's it going", 0.4, "speaker_0")
    b, end_b = say("Not bad Can't complain", end_a + 0.4, "speaker_1")
    c, _ = say("Good to hear good to hear", end_b + 0.4, "speaker_0")
    return words(*(a + b + c))


class GoodTakeTests(unittest.TestCase):
    def setUp(self):
        self.result = dialogue_receipt.check_dialogue(SCENE, clean_transcript())

    def test_a_conforming_take_passes_every_check(self):
        failed = [c["check"] for c in self.result["checks"] if not c["ok"]]
        self.assertEqual(failed, [], dialogue_receipt.render(self.result))

    def test_every_check_names_its_source(self):
        for check in self.result["checks"]:
            self.assertTrue(check["traces_to"], check["check"])

    def test_receipt_renders(self):
        self.assertIn("checks pass", dialogue_receipt.render(self.result))


class RedGateTests(unittest.TestCase):
    """Each test breaks exactly one thing and asserts the matching check fails."""

    def assertFails(self, result, check_name):
        failed = {c["check"] for c in result["checks"] if not c["ok"]}
        self.assertIn(check_name, failed, dialogue_receipt.render(result))

    def assertPasses(self, result, check_name):
        failed = {c["check"] for c in result["checks"] if not c["ok"]}
        self.assertNotIn(check_name, failed, dialogue_receipt.render(result))

    def test_catches_a_missing_line(self):
        a, end_a = say("Hey how's it going", 0.4, "speaker_0")
        c, _ = say("Good to hear good to hear", end_a + 0.4, "speaker_0")
        result = dialogue_receipt.check_dialogue(SCENE, words(*(a + c)))
        self.assertFails(result, "line_present:1:MAC")

    def test_catches_invented_speech(self):
        """The 2026-08-22 phantom line: a stem carrying words nobody scripted."""
        a, end_a = say("Hey how's it going", 0.4, "speaker_0")
        junk, end_j = say("who's asking", end_a + 0.4, "speaker_1")
        b, end_b = say("Not bad Can't complain", end_j + 0.4, "speaker_1")
        c, _ = say("Good to hear good to hear", end_b + 0.4, "speaker_0")
        result = dialogue_receipt.check_dialogue(SCENE, words(*(a + junk + b + c)))
        self.assertFails(result, "no_invented_speech")

    def test_stem_mode_catches_the_other_character(self):
        """A VOICE stem that also speaks MAC's line -- the real session-4 defect."""
        result = dialogue_receipt.check_dialogue(SCENE, clean_transcript(), only_speaker="VOICE")
        self.assertFails(result, "no_invented_speech")

    def test_stem_mode_passes_a_clean_stem(self):
        a, end_a = say("Hey how's it going", 0.4, "speaker_0")
        c, _ = say("Good to hear good to hear", end_a + 2.4, "speaker_0")
        result = dialogue_receipt.check_dialogue(SCENE, words(*(a + c)), only_speaker="VOICE")
        self.assertPasses(result, "no_invented_speech")

    def test_catches_overlapping_lines(self):
        a, end_a = say("Hey how's it going", 0.4, "speaker_0")
        b, end_b = say("Not bad Can't complain", end_a - 0.5, "speaker_1")
        c, _ = say("Good to hear good to hear", end_b + 0.4, "speaker_0")
        result = dialogue_receipt.check_dialogue(SCENE, words(*(a + b + c)))
        self.assertFails(result, "no_overlap")

    def test_catches_a_mid_line_pause(self):
        """The 2026-08-22 straggle: 'Not bad.' ... 'Can't complain.'"""
        a, end_a = say("Hey how's it going", 0.4, "speaker_0")
        first, end_1 = say("Not bad", end_a + 0.4, "speaker_1")
        second, end_2 = say("Can't complain", end_1 + 0.9, "speaker_1")
        c, _ = say("Good to hear good to hear", end_2 + 0.4, "speaker_0")
        result = dialogue_receipt.check_dialogue(SCENE, words(*(a + first + second + c)))
        self.assertFails(result, "no_internal_straggle")

    def test_per_line_budget_is_tighter_than_the_scene_default(self):
        """MAC's 0.15s budget must bite where the 0.5s scene default would not."""
        a, end_a = say("Hey how's it going", 0.4, "speaker_0")
        first, end_1 = say("Not bad", end_a + 0.4, "speaker_1")
        second, end_2 = say("Can't complain", end_1 + 0.30, "speaker_1")
        c, _ = say("Good to hear good to hear", end_2 + 0.4, "speaker_0")
        result = dialogue_receipt.check_dialogue(SCENE, words(*(a + first + second + c)))
        self.assertFails(result, "no_internal_straggle")

    def test_catches_one_voice_playing_both_characters(self):
        """The defect that opened session 4: the deep voice spoke MAC's line too."""
        a, end_a = say("Hey how's it going", 0.4, "speaker_0")
        b, end_b = say("Not bad Can't complain", end_a + 0.4, "speaker_0")
        c, _ = say("Good to hear good to hear", end_b + 0.4, "speaker_0")
        result = dialogue_receipt.check_dialogue(SCENE, words(*(a + b + c)))
        self.assertFails(result, "characters_are_distinct")

    def test_catches_a_character_recast_mid_scene(self):
        scene = {
            "clip_duration_s": 10.062,
            "lines": [
                {"speaker": "VOICE", "text": "Hey, how's it going?"},
                {"speaker": "VOICE", "text": "Good to hear, good to hear."},
            ],
        }
        a, end_a = say("Hey how's it going", 0.4, "speaker_0")
        c, _ = say("Good to hear good to hear", end_a + 0.4, "speaker_9")
        result = dialogue_receipt.check_dialogue(scene, words(*(a + c)))
        self.assertFails(result, "one_voice_per_character")

    def test_catches_speech_running_past_the_clip(self):
        a, end_a = say("Hey how's it going", 8.0, "speaker_0")
        b, end_b = say("Not bad Can't complain", end_a + 0.4, "speaker_1")
        c, _ = say("Good to hear good to hear", end_b + 0.4, "speaker_0")
        result = dialogue_receipt.check_dialogue(SCENE, words(*(a + b + c)))
        self.assertFails(result, "fits_clip")


class ParsingTests(unittest.TestCase):
    def test_normalize_strips_punctuation_but_keeps_apostrophes(self):
        self.assertEqual(dialogue_receipt.normalize("Not bad. Can't complain!"),
                         ["not", "bad", "can't", "complain"])

    def test_load_words_accepts_bare_list_and_wrapped_object(self):
        payload = [{"text": "hey", "start": 0.0, "end": 0.2, "type": "word"}]
        with tempfile.TemporaryDirectory() as tmp:
            bare = os.path.join(tmp, "a.json")
            wrapped = os.path.join(tmp, "b.json")
            with open(bare, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            with open(wrapped, "w", encoding="utf-8") as fh:
                json.dump({"words": payload}, fh)
            self.assertEqual(len(dialogue_receipt.load_words(bare)), 1)
            self.assertEqual(len(dialogue_receipt.load_words(wrapped)), 1)

    def test_load_words_drops_non_word_entries(self):
        payload = [
            {"text": "hey", "start": 0.0, "end": 0.2, "type": "word"},
            {"text": " ", "start": 0.2, "end": 0.3, "type": "spacing"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "w.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            self.assertEqual([w["text"] for w in dialogue_receipt.load_words(path)], ["hey"])


class SceneScriptTests(unittest.TestCase):
    """The shipped scene must stay loadable and keep the Director's direction."""

    def test_night_street_scene_is_valid(self):
        with open(SCENE_PATH, "r", encoding="utf-8") as handle:
            scene = json.load(handle)
        self.assertEqual(len(scene["lines"]), 4)
        self.assertEqual([ln["speaker"] for ln in scene["lines"]],
                         ["VOICE", "MAC", "VOICE", "VOICE"])

    def test_mac_line_carries_the_no_pause_direction(self):
        with open(SCENE_PATH, "r", encoding="utf-8") as handle:
            scene = json.load(handle)
        mac = [ln for ln in scene["lines"] if ln["speaker"] == "MAC"][0]
        self.assertLessEqual(mac["max_gap_s"], 0.15)
        self.assertIn("direction", mac)


if __name__ == "__main__":
    unittest.main()


class CliContractTests(unittest.TestCase):
    """Exit codes and the structured error shape are part of the CLI contract.

    A contract failure (1) and a tool failure (2) must stay distinguishable:
    in CI the first wants its receipt read, the second means the invocation is
    wrong. Errors carry code/message/hint and never a raw traceback.
    """

    def _run(self, argv):
        import contextlib, io
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = dialogue_receipt.main(argv)
        return code, out.getvalue(), err.getvalue()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.scene = os.path.join(self.tmp.name, "scene.json")
        self.words = os.path.join(self.tmp.name, "words.json")
        with open(self.scene, "w", encoding="utf-8") as fh:
            json.dump(SCENE, fh)
        with open(self.words, "w", encoding="utf-8") as fh:
            json.dump(clean_transcript(), fh)

    def test_clean_take_exits_zero(self):
        code, _, _ = self._run([self.scene, self.words])
        self.assertEqual(code, 0)

    def test_contract_failure_exits_one(self):
        bad = os.path.join(self.tmp.name, "bad.json")
        a, end_a = say("Hey how's it going", 0.4, "speaker_0")
        with open(bad, "w", encoding="utf-8") as fh:
            json.dump([{"text": t, "start": s, "end": e, "speaker_id": k, "type": "word"}
                       for t, s, e, k in a], fh)
        code, _, _ = self._run([self.scene, bad])
        self.assertEqual(code, 1)

    def test_missing_scene_exits_two_with_structured_error(self):
        code, _, err = self._run([os.path.join(self.tmp.name, "nope.json"), self.words])
        self.assertEqual(code, 2)
        payload = json.loads(err)["error"]
        self.assertEqual(payload["code"], "scene_not_found")
        self.assertTrue(payload["message"])
        self.assertTrue(payload["hint"])

    def test_missing_words_exits_two(self):
        code, _, err = self._run([self.scene, os.path.join(self.tmp.name, "nope.json")])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(err)["error"]["code"], "words_not_found")

    def test_malformed_json_exits_two_without_a_traceback(self):
        junk = os.path.join(self.tmp.name, "junk.json")
        with open(junk, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        code, _, err = self._run([junk, self.words])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(err)["error"]["code"], "scene_malformed")
        self.assertNotIn("Traceback", err)

    def test_only_speaker_naming_nobody_is_a_runtime_error_not_a_pass(self):
        """A misspelled --only-speaker must NOT pass vacuously.

        An empty contract satisfies every check, which is the most dangerous
        possible result: it renders as success.
        """
        code, _, err = self._run([self.scene, self.words, "--only-speaker", "NOBODY"])
        self.assertEqual(code, 2)
        payload = json.loads(err)["error"]
        self.assertEqual(payload["code"], "unknown_speaker")
        self.assertIn("MAC", payload["hint"])

    def test_scene_with_no_lines_is_a_runtime_error(self):
        empty = os.path.join(self.tmp.name, "empty.json")
        with open(empty, "w", encoding="utf-8") as fh:
            json.dump({"clip_duration_s": 10.0, "lines": []}, fh)
        code, _, err = self._run([empty, self.words])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(err)["error"]["code"], "empty_contract")

    def test_only_speaker_is_case_sensitive(self):
        code, _, err = self._run([self.scene, self.words, "--only-speaker", "mac"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(err)["error"]["code"], "unknown_speaker")

    def test_debug_flag_re_raises(self):
        with self.assertRaises(FileNotFoundError):
            dialogue_receipt.main([os.path.join(self.tmp.name, "nope.json"),
                                   self.words, "--debug"])
