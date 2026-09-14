"""Tests for ``fxdub.verify`` — the declared public API.

Three kinds of gate live here, and the second two matter more than the first:

1. **Contract tests** — the exported surface behaves as its docstrings promise.
2. **Foreign-defect tests** — the four failures a dogfood swarm measured in
   ``mcp-tool-shop-org/audiobooker``, an EPUB→audiobook renderer with no video,
   no bed and no concurrent speakers. Its 1235 passing tests could not see any
   of them, because every one is a defect in what the audio *says*. They are
   here because a check proven only against the medium it was written for is not
   yet evidence that it generalizes — and a **clean control** is here beside
   them, because a check that only ever fires is as broken as one that never
   does.
3. **Delegation tests** — mechanical proof that ``dialogue_receipt`` computes
   its content verdicts *through* this module rather than beside it. A public
   API the shipping tool does not itself use is a path nobody dogfoods, and it
   drifts.
"""

from __future__ import annotations

import ast
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import dialogue_receipt  # noqa: E402
import verify  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def words(*specs, rate=0.30, gap=0.05):
    """Build a diarized word list from ``(text, speaker)`` pairs, laid out in time.

    Mirrors the layout helper from the audiobooker feasibility probe so the
    fixtures below are the shapes that probe measured, not paraphrases of them.
    """
    out, t = [], 0.0
    for text, speaker in specs:
        for token in text.split():
            out.append({"text": token, "start": round(t, 3),
                        "end": round(t + rate, 3), "speaker": speaker})
            t += rate + gap
        t += 0.25
    return out


def verdicts(result):
    """The three medium-agnostic checks, keyed by name."""
    return {c.name: c for c in (verify.check_all_lines_present(result),
                                verify.check_no_invented_speech(result),
                                verify.check_one_voice_per_line(result))}


# ---------------------------------------------------------------------------
# 1. Contract
# ---------------------------------------------------------------------------

class NormalizeTextTests(unittest.TestCase):
    def test_lowercases_and_drops_punctuation(self):
        self.assertEqual(verify.normalize_text("Not bad. Can't complain!"),
                         ["not", "bad", "can't", "complain"])

    def test_keeps_apostrophes(self):
        """Documented on purpose: dropping the mark makes a receipt unreadable."""
        self.assertIn("can't", verify.normalize_text("Can't"))
        self.assertNotIn("cant", verify.normalize_text("Can't"))

    def test_empty_and_none_yield_no_tokens(self):
        self.assertEqual(verify.normalize_text(""), [])
        self.assertEqual(verify.normalize_text(None), [])


class NormalizeWordsTests(unittest.TestCase):
    RAW = [{"text": "Hello,", "start": 0.0, "end": 0.4, "speaker_id": "s0", "type": "word"}]

    def test_accepts_a_bare_list(self):
        self.assertEqual(len(verify.normalize_words(self.RAW)), 1)

    def test_accepts_an_object_with_a_words_key(self):
        self.assertEqual(len(verify.normalize_words({"words": self.RAW})), 1)

    def test_is_idempotent(self):
        """A caller may normalize defensively without checking whether it happened."""
        once = verify.normalize_words(self.RAW)
        self.assertEqual(verify.normalize_words(once), once)

    def test_prefers_speaker_id_and_falls_back_to_speaker(self):
        both = verify.normalize_words([{"text": "a", "speaker_id": "x", "speaker": "y"}])
        only = verify.normalize_words([{"text": "a", "speaker": "y"}])
        self.assertEqual(both[0]["speaker"], "x")
        self.assertEqual(only[0]["speaker"], "y")

    def test_drops_non_word_entries(self):
        raw = self.RAW + [{"text": " ", "start": 0.4, "end": 0.5, "type": "spacing"},
                          {"text": "(laughs)", "start": 0.5, "end": 0.9, "type": "audio_event"}]
        self.assertEqual([w["text"] for w in verify.normalize_words(raw)], ["hello"])

    def test_drops_non_dict_entries_and_empty_text(self):
        raw = self.RAW + ["junk", None, {"text": "!!!", "start": 1.0, "end": 1.1}]
        self.assertEqual([w["text"] for w in verify.normalize_words(raw)], ["hello"])

    def test_missing_times_default_to_zero(self):
        self.assertEqual(verify.normalize_words([{"text": "a"}])[0]["start"], 0.0)

    def test_a_fused_entry_keeps_every_token(self):
        fused = verify.normalize_words([{"text": "New York", "start": 0.0, "end": 1.0}])
        self.assertEqual(fused[0]["tokens"], ["new", "york"])

    def test_rejects_input_that_is_neither_list_nor_mapping(self):
        with self.assertRaises(TypeError) as caught:
            verify.normalize_words(None)
        self.assertIn("words", str(caught.exception))


class AlignLinesTests(unittest.TestCase):
    LINES = [{"speaker": "A", "text": "Hello there."},
             {"speaker": "B", "text": "General Kenobi."}]

    def clean(self):
        return words(("Hello there", "s0"), ("General Kenobi", "s1"))

    def test_matches_every_line_and_reports_its_span(self):
        result = verify.align_lines(self.LINES, self.clean())
        self.assertEqual([m["found"] for m in result.matched], [True, True])
        self.assertLess(result.matched[0]["start"], result.matched[1]["start"])

    def test_accepts_raw_pre_normalized_and_wrapped_input_alike(self):
        raw = self.clean()
        for label, payload in (("raw list", raw),
                               ("wrapped", {"words": raw}),
                               ("pre-normalized", verify.normalize_words(raw))):
            with self.subTest(shape=label):
                result = verify.align_lines(self.LINES, payload)
                self.assertEqual(result.missing, [])

    def test_a_missing_line_is_a_finding_not_an_exception(self):
        result = verify.align_lines(self.LINES, words(("Hello there", "s0")))
        self.assertEqual(len(result.missing), 1)
        self.assertEqual(result.missing[0]["speaker"], "B")
        self.assertEqual(result.matched[0]["found"], True,
                         "the other lines must still be reported")

    def test_a_missing_line_carries_no_measurements(self):
        result = verify.align_lines(self.LINES, words(("Hello there", "s0")))
        self.assertNotIn("start", result.missing[0])

    def test_lines_are_matched_in_script_order(self):
        """B's text spoken BEFORE A's does not satisfy B — order is part of the contract."""
        result = verify.align_lines(
            self.LINES, words(("General Kenobi", "s1"), ("Hello there", "s0")))
        self.assertEqual([m["found"] for m in result.matched], [True, False])

    def test_diarized_speaker_is_a_majority_vote(self):
        """Two tokens from s0, one from s1 -- the line reads as s0's."""
        result = verify.align_lines(
            [{"speaker": "A", "text": "one two three"}],
            words(("one two", "s0"), ("three", "s1")))
        self.assertEqual(result.matched[0]["diarized_speaker"], "s0")

    def test_an_undiarized_transcript_yields_no_speaker(self):
        result = verify.align_lines([{"speaker": "A", "text": "one"}],
                                    [{"text": "one", "start": 0.0, "end": 0.3}])
        self.assertIsNone(result.matched[0]["diarized_speaker"])

    def test_max_gap_s_is_carried_through_untouched(self):
        result = verify.align_lines([{"speaker": "A", "text": "one", "max_gap_s": 0.15}],
                                    words(("one", "s0")))
        self.assertEqual(result.matched[0]["max_gap_s"], 0.15)

    def test_internal_gap_is_measured(self):
        late = [{"text": "one", "start": 0.0, "end": 0.3, "speaker": "s0"},
                {"text": "two", "start": 1.2, "end": 1.5, "speaker": "s0"}]
        result = verify.align_lines([{"speaker": "A", "text": "one two"}], late)
        self.assertAlmostEqual(result.matched[0]["max_internal_gap_s"], 0.9, places=3)

    def test_a_fused_transcript_entry_still_aligns(self):
        fused = [{"text": "Hello there", "start": 0.0, "end": 1.0, "speaker": "s0"},
                 {"text": "General Kenobi", "start": 1.2, "end": 2.2, "speaker": "s1"}]
        self.assertEqual(verify.align_lines(self.LINES, fused).missing, [])

    def test_an_empty_script_claims_nothing(self):
        result = verify.align_lines([], self.clean())
        self.assertEqual(result.matched, [])
        self.assertEqual(len(result.invented_words), 4,
                         "every rendered token is unscripted when nothing was scripted")

    def test_performs_no_io(self):
        """Documented promise: the alignment core touches no filesystem."""
        self.assertNotIn("open", verify.align_lines.__code__.co_names)


class AlignResultTests(unittest.TestCase):
    def setUp(self):
        self.result = verify.align_lines(
            [{"speaker": "A", "text": "one"}, {"speaker": "B", "text": "two"}],
            words(("one", "s0"), ("three", "s1")))

    def test_missing_lists_unfound_lines_in_script_order(self):
        self.assertEqual([m["speaker"] for m in self.result.missing], ["B"])

    def test_invented_words_is_the_unconsumed_list_under_its_meaning(self):
        self.assertIs(self.result.invented_words, self.result.unconsumed)
        self.assertEqual([w["text"] for w in self.result.invented_words], ["three"])

    def test_the_result_is_frozen(self):
        with self.assertRaises(Exception):
            self.result.matched = []


class CheckTests(unittest.TestCase):
    def test_as_dict_uses_the_receipt_row_vocabulary(self):
        row = verify.Check("n", True, "d", "t").as_dict()
        self.assertEqual(row, {"check": "n", "ok": True, "detail": "d", "traces_to": "t"})

    def test_every_check_names_what_it_traces_to(self):
        result = verify.align_lines([{"speaker": "A", "text": "one"}], words(("one", "s0")))
        for name, check in verdicts(result).items():
            with self.subTest(check=name):
                self.assertTrue(check.traces_to,
                                "a check nobody can justify should be deleted, not shipped")
                self.assertTrue(check.detail)


class CastingMapTests(unittest.TestCase):
    def test_maps_each_speaker_to_the_voices_that_rendered_them(self):
        result = verify.align_lines(
            [{"speaker": "A", "text": "one"}, {"speaker": "B", "text": "two"}],
            words(("one", "s0"), ("two", "s1")))
        self.assertEqual(verify.casting_map(result), {"A": ["s0"], "B": ["s1"]})

    def test_a_recast_speaker_maps_to_two_voices(self):
        result = verify.align_lines(
            [{"speaker": "A", "text": "one"}, {"speaker": "A", "text": "two"}],
            words(("one", "s0"), ("two", "s9")))
        self.assertEqual(verify.casting_map(result), {"A": ["s0", "s9"]})

    def test_an_undiarized_transcript_evidences_no_casting(self):
        result = verify.align_lines([{"speaker": "A", "text": "one"}],
                                    [{"text": "one", "start": 0.0, "end": 0.3}])
        self.assertEqual(verify.casting_map(result), {},
                         "no evidence must not read as clean evidence")

    def test_a_missing_line_contributes_nothing(self):
        result = verify.align_lines(
            [{"speaker": "A", "text": "one"}, {"speaker": "GHOST", "text": "nowhere"}],
            words(("one", "s0")))
        self.assertNotIn("GHOST", verify.casting_map(result))


# ---------------------------------------------------------------------------
# 1b. Red gates — every check must be able to fail
# ---------------------------------------------------------------------------

class RedGateTests(unittest.TestCase):
    """A check that cannot go red is theater. Prove each of the three fires."""

    def test_all_lines_present_goes_red(self):
        result = verify.align_lines(
            [{"speaker": "A", "text": "one"}, {"speaker": "B", "text": "two"}],
            words(("one", "s0")))
        check = verify.check_all_lines_present(result)
        self.assertFalse(check.ok)
        self.assertIn("1 of 2", check.detail)
        self.assertIn("two", check.detail, "the receipt must name which line is missing")

    def test_no_invented_speech_goes_red(self):
        result = verify.align_lines([{"speaker": "A", "text": "one"}],
                                    words(("one", "s0"), ("surprise", "s1")))
        check = verify.check_no_invented_speech(result)
        self.assertFalse(check.ok)
        self.assertIn("surprise", check.detail)

    def test_one_voice_per_line_goes_red_on_a_recast_character(self):
        result = verify.align_lines(
            [{"speaker": "A", "text": "one"}, {"speaker": "A", "text": "two"}],
            words(("one", "s0"), ("two", "s9")))
        check = verify.check_one_voice_per_line(result)
        self.assertFalse(check.ok)
        self.assertIn("2 voices", check.detail)

    def test_one_voice_per_line_goes_red_on_two_characters_sharing_a_voice(self):
        result = verify.align_lines(
            [{"speaker": "A", "text": "one"}, {"speaker": "B", "text": "two"}],
            words(("one", "s0"), ("two", "s0")))
        check = verify.check_one_voice_per_line(result)
        self.assertFalse(check.ok)
        self.assertIn("one voice", check.detail)

    def test_one_voice_per_line_makes_no_claim_without_speaker_ids(self):
        """Silence is not a pass. It must say so, so nobody reads it as one."""
        result = verify.align_lines([{"speaker": "A", "text": "one"}],
                                    [{"text": "one", "start": 0.0, "end": 0.3}])
        check = verify.check_one_voice_per_line(result)
        self.assertTrue(check.ok)
        self.assertIn("not evidenced", check.detail)


# ---------------------------------------------------------------------------
# 2. The foreign defects — measured in audiobooker, an EPUB→audiobook renderer
# ---------------------------------------------------------------------------

class AudiobookerDefectTests(unittest.TestCase):
    """Four real defects from another repo, and a control that must stay quiet.

    Sources: a dogfood swarm on ``mcp-tool-shop-org/audiobooker`` (2026-09-14)
    found 3 CRITICAL and 34 HIGH defects behind 1235 passing tests. These four
    are the ones about what the audio *says*. None of them involves video, a
    music bed, or two characters speaking at once — which is the point. If this
    API only caught fx-dub's own failures, it would not be worth declaring.
    """

    def test_a_sentinel_token_narrated_aloud_is_caught(self):
        """audiobooker CRITICAL: process_footnotes() never ran, so the narrator
        read the literal marker on essentially every EPUB."""
        result = verify.align_lines(
            [{"speaker": "narrator", "text": "She was born in the 1st century, they said."}],
            words(("She was born in the FOOTNOTE START st FOOTNOTE END century they said",
                   "narrator")))
        checks = verdicts(result)
        self.assertFalse(checks["all_lines_present"].ok,
                         "the scripted line was not spoken as written")
        self.assertFalse(checks["no_invented_speech"].ok)
        self.assertIn("footnote", checks["no_invented_speech"].detail)

    def test_a_dropped_chapter_reported_as_success_is_caught(self):
        """audiobooker CRITICAL: --allow-partial shipped 29 of 30 chapters and
        reported status=success. A short audiobook is still a valid file."""
        result = verify.align_lines(
            [{"speaker": "narrator", "text": "Chapter one begins here."},
             {"speaker": "narrator", "text": "Chapter two continues the tale."},
             {"speaker": "narrator", "text": "Chapter three ends it."}],
            words(("Chapter one begins here", "narrator"),
                  ("Chapter three ends it", "narrator")))
        checks = verdicts(result)
        self.assertFalse(checks["all_lines_present"].ok)
        self.assertIn("Chapter two", checks["all_lines_present"].detail,
                      "the receipt must name the chapter that vanished")
        self.assertTrue(checks["no_invented_speech"].ok,
                        "a dropped chapter must not also read as invented speech")

    def test_three_characters_collapsed_into_one_voice_is_caught(self):
        """audiobooker HIGH: leftmost-wins attribution gave every quote one voice."""
        result = verify.align_lines(
            [{"speaker": "Alice", "text": "Hello."},
             {"speaker": "Bob", "text": "Goodbye."},
             {"speaker": "Carol", "text": "Wait."}],
            words(("Hello", "Alice"), ("Goodbye", "Alice"), ("Wait", "Alice")))
        check = verdicts(result)["one_voice_per_line"]
        self.assertFalse(check.ok)
        for who in ("Alice", "Bob", "Carol"):
            self.assertIn(who, check.detail)

    def test_a_malformed_review_tag_narrated_as_prose_is_caught(self):
        """audiobooker HIGH: an unparseable @tag was absorbed into the body and
        narrated, so the listener heard the markup."""
        result = verify.align_lines(
            [{"speaker": "narrator", "text": "The shop was warm."},
             {"speaker": "Bob, the baker", "text": "Fresh bread!"}],
            words(("The shop was warm at Bob the baker Fresh bread", "narrator")))
        checks = verdicts(result)
        self.assertFalse(checks["no_invented_speech"].ok)
        self.assertIn("bob", checks["no_invented_speech"].detail)
        self.assertFalse(checks["one_voice_per_line"].ok,
                         "the baker's line was rendered in the narrator's voice")

    def test_the_control_render_reports_nothing(self):
        """The half that makes the four above mean something.

        A detector that fires on correct output is not a verifier, it is noise
        with a receipt — and noise gets muted, which is how a real finding goes
        unread.
        """
        result = verify.align_lines(
            [{"speaker": "Alice", "text": "Hello."},
             {"speaker": "Bob", "text": "Goodbye."}],
            words(("Hello", "Alice"), ("Goodbye", "Bob")))
        for name, check in verdicts(result).items():
            with self.subTest(check=name):
                self.assertTrue(check.ok, check.detail)


# ---------------------------------------------------------------------------
# 3. Delegation — dialogue_receipt must compute through verify, not beside it
# ---------------------------------------------------------------------------

SCENE = {
    "clip_duration_s": 10.062,
    "lines": [{"speaker": "VOICE", "text": "Hey, how's it going?"},
              {"speaker": "MAC", "text": "Not bad."}],
}
TRANSCRIPT = words(("Hey how's it going", "s0"), ("Not bad", "s1"))


class DelegationTests(unittest.TestCase):
    """Proof that the CLI is a CONSUMER of the public API.

    The requirement is load-bearing: if ``dialogue_receipt`` kept a private copy
    of the alignment core, the public surface would be a path the shipping tool
    never exercises, and the two would drift apart silently. That is the same
    shape as the defect that started this work — audiobooker's ``master_check()``
    was correct code that no render path ever called, so its compliance claim
    went unverified for two major versions.

    These tests break ``verify`` and require the CLI to break with it. A parallel
    implementation would survive them.
    """

    def _sabotage(self, name):
        """Replace a verify function with one that refuses to run, and restore it."""
        original = getattr(verify, name)

        def refuse(*args, **kwargs):
            raise AssertionError(
                "verify.{0} was bypassed — dialogue_receipt has grown a parallel "
                "implementation".format(name))

        setattr(verify, name, refuse)
        self.addCleanup(setattr, verify, name, original)

    def test_check_dialogue_aligns_through_verify(self):
        self._sabotage("align_lines")
        with self.assertRaises(AssertionError):
            dialogue_receipt.check_dialogue(SCENE, TRANSCRIPT)

    def test_check_dialogue_takes_its_invented_speech_verdict_from_verify(self):
        self._sabotage("check_no_invented_speech")
        with self.assertRaises(AssertionError):
            dialogue_receipt.check_dialogue(SCENE, TRANSCRIPT)

    def test_check_dialogue_takes_its_casting_map_from_verify(self):
        self._sabotage("casting_map")
        with self.assertRaises(AssertionError):
            dialogue_receipt.check_dialogue(SCENE, TRANSCRIPT)

    def test_the_legacy_align_helper_delegates(self):
        self._sabotage("align_lines")
        with self.assertRaises(AssertionError):
            dialogue_receipt.align(SCENE["lines"], TRANSCRIPT)

    def test_the_tokenizer_is_shared_not_copied(self):
        self.assertIs(dialogue_receipt.normalize, verify.normalize_text)
        self.assertIs(dialogue_receipt.normalize_words, verify.normalize_words)

    def test_the_cli_keeps_no_private_word_machinery(self):
        for attribute in ("_PUNCT", "_flatten"):
            with self.subTest(attribute=attribute):
                self.assertFalse(
                    hasattr(dialogue_receipt, attribute),
                    "dialogue_receipt.{0} is back — the word handling has been "
                    "duplicated out of verify".format(attribute))

    def test_the_legacy_align_returns_the_same_measurements_as_the_public_api(self):
        matched, unconsumed = dialogue_receipt.align(SCENE["lines"], TRANSCRIPT)
        result = verify.align_lines(SCENE["lines"], TRANSCRIPT)
        self.assertEqual(matched, result.matched)
        self.assertEqual(unconsumed, result.unconsumed)


class ReceiptAgreementTests(unittest.TestCase):
    """The receipt's per-line rows and the API's aggregate must never disagree.

    The CLI reports one row per scripted line because whoever reads a dub receipt
    is deciding which line to re-render, and "1 of 4 missing" does not tell them
    which. That is a different *rendering* of the same measurement — and this is
    the gate that keeps it from becoming a different measurement.
    """

    def _rows_and_aggregate(self, scene, transcript):
        receipt = dialogue_receipt.check_dialogue(scene, transcript)
        rows = {c["check"]: c["ok"] for c in receipt["checks"]
                if c["check"].startswith("line_present:")}
        aggregate = verify.check_all_lines_present(
            verify.align_lines(scene["lines"], transcript))
        return rows, aggregate

    def test_agree_on_a_clean_take(self):
        rows, aggregate = self._rows_and_aggregate(SCENE, TRANSCRIPT)
        self.assertTrue(all(rows.values()))
        self.assertTrue(aggregate.ok)

    def test_agree_on_a_missing_line(self):
        rows, aggregate = self._rows_and_aggregate(SCENE, words(("Hey how's it going", "s0")))
        self.assertEqual(rows["line_present:1:MAC"], False)
        self.assertFalse(aggregate.ok)
        self.assertEqual(sum(1 for ok in rows.values() if not ok), 1)
        self.assertIn("1 of 2", aggregate.detail)

    def test_the_invented_speech_row_is_the_api_verdict_verbatim(self):
        transcript = TRANSCRIPT + words(("surprise", "s1"))
        receipt = dialogue_receipt.check_dialogue(SCENE, transcript)
        row = [c for c in receipt["checks"] if c["check"] == "no_invented_speech"][0]
        expected = verify.check_no_invented_speech(
            verify.align_lines(SCENE["lines"], transcript)).as_dict()
        self.assertEqual(row, expected)


class PublicSurfaceTests(unittest.TestCase):
    """What ``__all__`` promises must exist, and must not quietly grow."""

    EXPECTED = {
        "Word", "Line", "MatchedLine", "AlignResult", "Check",
        "normalize_text", "normalize_words", "align_lines", "casting_map",
        "check_all_lines_present", "check_no_invented_speech",
        "check_one_voice_per_line",
    }

    def test_all_declares_exactly_the_documented_surface(self):
        self.assertEqual(set(verify.__all__), self.EXPECTED)

    def test_every_declared_name_exists(self):
        for name in verify.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(verify, name))

    def test_every_public_symbol_documents_its_contract(self):
        """A declared API with an undocumented member is not declared, it is leaked."""
        for name in verify.__all__:
            with self.subTest(name=name):
                self.assertTrue((getattr(verify, name).__doc__ or "").strip(),
                                "{0} has no docstring".format(name))

    def test_the_module_imports_nothing_outside_the_standard_library(self):
        """Zero runtime dependencies is a promise SECURITY.md makes.

        pyproject is checked elsewhere; this checks the one module third parties
        import directly, where an added dependency would be easiest to miss.
        """
        allowed = {"__future__", "re", "dataclasses", "typing"}
        source = os.path.join(REPO_ROOT, "tools", "verify.py")
        with open(source, "r", encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(imported - allowed, set(),
                         "verify.py imports something outside {0}".format(sorted(allowed)))


if __name__ == "__main__":
    unittest.main()
