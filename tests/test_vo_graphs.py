"""Tests for ``tools/vo_graphs.py``.

Two obligations here. First, every builder must emit a structurally sound API
graph -- ``graph_lint.api_structural_findings`` is the same check the platform's
pre-flight runs, so a builder that fails it would have failed a submit.

Second, and the reason this file matters: every builder must come out CLEAN
under ``graph_lint.API_DETECTORS``. Those detectors encode traps that each cost
a real failed job on 2026-08-22. Wiring them to the builders means the shapes
that burned us cannot be re-authored by hand and quietly submitted again.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import graph_lint  # noqa: E402
import vo_graphs  # noqa: E402


def build_one_of_each():
    """Every builder, with arguments that reflect real use."""
    return {
        "bytedance_text_only": vo_graphs.bytedance_text_only(
            "A man speaks.\n\nNot bad, can't complain.", "fx/a", pitch_rate=-2),
        "bytedance_audio_reference": vo_graphs.bytedance_audio_reference(
            "ref.flac", "The speaker is @Audio1.\n\nHey.", "fx/b"),
        "elevenlabs_clone_tts": vo_graphs.elevenlabs_clone_tts(
            "ref.flac", "Hey there.", "fx/c"),
        "splice": vo_graphs.splice("clip.flac", [(0.3, 0.7), (2.7, 0.9)], "fx/d"),
        "place": vo_graphs.place("clip.flac", 2.28, "fx/e"),
        "mix": vo_graphs.mix("a.flac", "b.flac", "fx/f", gain_b_db=-12),
        "transcribe": vo_graphs.transcribe("clip.flac", "fx/g"),
    }


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.graphs = build_one_of_each()

    def test_every_builder_emits_a_sound_api_graph(self):
        for name, graph in self.graphs.items():
            findings = graph_lint.api_structural_findings(graph)
            self.assertEqual(findings, [], "{0}: {1}".format(name, graph_lint.describe(findings)))

    def test_every_builder_emits_a_non_empty_node_map(self):
        for name, graph in self.graphs.items():
            self.assertTrue(graph, name)
            for node_id, node in graph.items():
                self.assertIn("class_type", node, "{0}/{1}".format(name, node_id))

    def test_audio_producing_builders_terminate_in_a_saver(self):
        for name in ("bytedance_text_only", "bytedance_audio_reference",
                     "elevenlabs_clone_tts", "splice", "place", "mix"):
            types = {n["class_type"] for n in self.graphs[name].values()}
            self.assertIn("SaveAudioAdvanced", types, name)

    def test_transcribe_terminates_in_savetext(self):
        types = {n["class_type"] for n in self.graphs["transcribe"].values()}
        self.assertIn("SaveText", types)


class TrapComplianceTests(unittest.TestCase):
    """The builders must not reproduce any trap the detectors encode."""

    def test_no_builder_trips_a_blocking_detector(self):
        #: audio-reference mode always raises the verification marker by design;
        #: it is a "gate this output" flag, not a wiring defect.
        advisory = {"api_bytedance_reference_unverified"}
        for name, graph in build_one_of_each().items():
            fired = graph_lint.fired_api(graph) - advisory
            self.assertEqual(fired, set(), "{0} tripped {1}".format(name, fired))

    def test_clone_builder_uses_the_runtime_slot_name(self):
        graph = vo_graphs.elevenlabs_clone_tts("ref.flac", "hi", "fx/x")
        clone = [n for n in graph.values() if n["class_type"] == "ElevenLabsInstantVoiceClone"][0]
        self.assertIn("files.audio0", clone["inputs"])
        self.assertNotIn("files.item_1", clone["inputs"])

    def test_no_builder_emits_the_broken_audiopad_node(self):
        for name, graph in build_one_of_each().items():
            types = {n["class_type"] for n in graph.values()}
            self.assertNotIn("AudioPad", types, name)

    def test_audio_reference_builder_is_flagged_for_verification(self):
        graph = vo_graphs.bytedance_audio_reference("r.flac", "The speaker is @Audio1.", "fx/y")
        self.assertIn("api_bytedance_reference_unverified", graph_lint.fired_api(graph))

    def test_transcribe_respects_the_diarize_constraints(self):
        node = [n for n in vo_graphs.transcribe("c.flac", "p").values()
                if n["class_type"] == "ElevenLabsSpeechToText"][0]
        self.assertEqual(node["inputs"]["num_speakers"], 0)
        self.assertLessEqual(node["inputs"]["model.diarization_threshold"], 0.4)


class SpliceTests(unittest.TestCase):
    def test_single_span_needs_no_concat(self):
        graph = vo_graphs.splice("c.flac", [(0.0, 1.0)], "fx/s")
        self.assertNotIn("AudioConcat", {n["class_type"] for n in graph.values()})

    def test_three_spans_chain_two_concats(self):
        graph = vo_graphs.splice("c.flac", [(0, 1), (2, 1), (4, 1)], "fx/s")
        concats = [n for n in graph.values() if n["class_type"] == "AudioConcat"]
        self.assertEqual(len(concats), 2)

    def test_empty_spans_is_rejected(self):
        with self.assertRaises(ValueError):
            vo_graphs.splice("c.flac", [], "fx/s")

    def test_spans_are_trimmed_in_order(self):
        graph = vo_graphs.splice("c.flac", [(0.3, 0.7), (2.7, 0.9)], "fx/s")
        trims = [n["inputs"] for n in graph.values() if n["class_type"] == "TrimAudioDuration"]
        self.assertEqual(sorted(t["start_index"] for t in trims), [0.3, 2.7])


class GapClosingTests(unittest.TestCase):
    #: The real measurement from candidate A: 1.880s of dead air mid-line.
    WORDS = [
        {"text": "not", "start": 0.419, "end": 0.619},
        {"text": "bad", "start": 0.639, "end": 0.899},
        {"text": "can't", "start": 2.779, "end": 3.000},
        {"text": "complain", "start": 3.039, "end": 3.479},
    ]

    def test_closes_the_measured_gap_to_under_the_directors_budget(self):
        spans = vo_graphs.gap_closing_spans(self.WORDS, after_index=1)
        (s0, d0), (s1, _d1) = spans
        joined_gap = (s0 + d0 - self.WORDS[1]["end"]) + (self.WORDS[2]["start"] - s1)
        self.assertLess(joined_gap, 0.15, "gap after splice: {0:.3f}s".format(joined_gap))

    def test_keeps_every_word(self):
        (s0, d0), (s1, d1) = vo_graphs.gap_closing_spans(self.WORDS, after_index=1)
        self.assertLessEqual(s0, self.WORDS[0]["start"])
        self.assertGreaterEqual(s0 + d0, self.WORDS[1]["end"])
        self.assertLessEqual(s1, self.WORDS[2]["start"])
        self.assertGreaterEqual(s1 + d1, self.WORDS[-1]["end"])

    def test_spans_do_not_overlap_or_run_backwards(self):
        (s0, d0), (s1, d1) = vo_graphs.gap_closing_spans(self.WORDS, after_index=1)
        self.assertGreater(d0, 0)
        self.assertGreater(d1, 0)
        self.assertGreaterEqual(s1, s0 + d0 - 1e-9)

    def test_rejects_an_index_with_no_successor(self):
        with self.assertRaises(ValueError):
            vo_graphs.gap_closing_spans(self.WORDS, after_index=len(self.WORDS) - 1)


if __name__ == "__main__":
    unittest.main()
