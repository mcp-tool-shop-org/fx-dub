"""Red-gate tests for the API-format detectors in ``graph_lint``.

Each fixture below is a graph that ACTUALLY FAILED on Comfy Cloud on
2026-08-22, reduced to the nodes that matter. A detector that cannot go red on
the graph it was written for is theater, so every detector here is proven
against the real failure and proven silent on the real fix.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import graph_lint  # noqa: E402


#: FAILED: "Required input is missing ... {'input_name': 'files.audio0'}".
#: The name came from ``get_node``, which advertises the auto-grow slot as
#: ``files.item_1``. ``dry_run`` PASSED this graph.
CLONE_WRONG_SLOT = {
    "1": {"class_type": "LoadAudio", "inputs": {"audio": "ref.flac"}},
    "2": {"class_type": "ElevenLabsInstantVoiceClone",
          "inputs": {"files.item_1": ["1", 0], "remove_background_noise": False}},
}

#: SUCCEEDED: job 920dc2e0-e420-473a-9cb9-45b84b0fea65.
CLONE_RIGHT_SLOT = {
    "1": {"class_type": "LoadAudio", "inputs": {"audio": "ref.flac"}},
    "2": {"class_type": "ElevenLabsInstantVoiceClone",
          "inputs": {"files.audio0": ["1", 0], "remove_background_noise": False}},
}

#: FAILED: "FishAudioTextToSpeech.execute() got an unexpected keyword argument
#: 'model.voices.item_1'".
FISH_WRONG_VOICES = {
    "1": {"class_type": "FishAudioVoiceSelector", "inputs": {"voice": "Adrian (en)"}},
    "3": {"class_type": "FishAudioTextToSpeech",
          "inputs": {"text": "hi", "model": "s2.1-pro", "model.voices.item_1": ["1", 0]}},
}

#: SUCCEEDED: the s1 model takes a single ``model.voice``.
FISH_RIGHT_VOICE = {
    "1": {"class_type": "FishAudioVoiceSelector", "inputs": {"voice": "Adrian (en)"}},
    "3": {"class_type": "FishAudioTextToSpeech",
          "inputs": {"text": "hi", "model": "s1", "model.voice": ["1", 0]}},
}

#: FAILED: "UnboundLocalError: cannot access local variable 'pad_samples'".
USES_AUDIOPAD = {
    "2": {"class_type": "TrimAudioDuration", "inputs": {"audio": ["1", 0]}},
    "3": {"class_type": "AudioPad",
          "inputs": {"audio": ["2", 0], "pad_start_seconds": 2.28, "pad_end_seconds": 5.84}},
}

#: SUCCEEDED: the workaround that replaced it.
USES_EMPTYAUDIO_CONCAT = {
    "1": {"class_type": "EmptyAudio", "inputs": {"duration": 2.28, "sample_rate": 48000, "channels": 2}},
    "3": {"class_type": "TrimAudioDuration", "inputs": {"audio": ["2", 0]}},
    "4": {"class_type": "AudioConcat",
          "inputs": {"audio1": ["1", 0], "audio2": ["3", 0], "direction": "after"}},
}

#: RAN, BUT THE DIRECTOR REJECTED IT: pitch_rate -3 dragged both characters down,
#: so the visible character sounded like the off-frame one.
BYTEDANCE_GLOBAL_PITCH = {
    "1": {"class_type": "ByteDanceSeedAudio", "inputs": {
        "text_prompt": "Two men talk.\n\n[0.4s:2.0s] VOICE: Hey, how's it going?\n"
                       "[2.3s:4.0s] MAC: Not bad. Can't complain.",
        "reference_mode": "text only", "pitch_rate": -3, "sample_rate": "48000"}},
}

#: The fix: one pass per character, so each carries its own pitch.
BYTEDANCE_ONE_CHARACTER = {
    "1": {"class_type": "ByteDanceSeedAudio", "inputs": {
        "text_prompt": "A man speaks.\n\n[0.4s:2.0s] Hey, how's it going?",
        "reference_mode": "text only", "pitch_rate": -3, "sample_rate": "48000"}},
}

#: RAN, AND SHIPPED A DEFECT: the reference clip carried four lines, so the model
#: re-spoke a line the prompt omitted.
BYTEDANCE_AUDIO_REFERENCE = {
    "1": {"class_type": "LoadAudio", "inputs": {"audio": "scene.flac"}},
    "2": {"class_type": "ByteDanceSeedAudio", "inputs": {
        "text_prompt": "The speaker is @Audio1.\n\n[0.4s:2.0s] Hey, how's it going?",
        "reference_mode": "audio reference",
        "reference_mode.reference_audio_1": ["1", 0],
        "pitch_rate": 0, "sample_rate": "48000"}},
}


class AutogrowSlotTests(unittest.TestCase):
    def test_fires_on_the_graph_that_failed(self):
        self.assertIn("api_autogrow_slot_name", graph_lint.fired_api(CLONE_WRONG_SLOT))

    def test_silent_on_the_graph_that_ran(self):
        self.assertNotIn("api_autogrow_slot_name", graph_lint.fired_api(CLONE_RIGHT_SLOT))

    def test_finding_names_the_runtime_slot(self):
        findings = graph_lint.api_autogrow_slot_name(CLONE_WRONG_SLOT)
        self.assertTrue(any("files.audio0" in f.detail for f in findings))

    def test_finding_warns_that_dry_run_misses_it(self):
        findings = graph_lint.api_autogrow_slot_name(CLONE_WRONG_SLOT)
        self.assertTrue(any("dry_run" in f.detail for f in findings))


class FishVoicesTests(unittest.TestCase):
    def test_fires_on_the_graph_that_failed(self):
        self.assertIn("api_fish_autogrow_voices", graph_lint.fired_api(FISH_WRONG_VOICES))

    def test_silent_on_the_graph_that_ran(self):
        self.assertNotIn("api_fish_autogrow_voices", graph_lint.fired_api(FISH_RIGHT_VOICE))


class BrokenNodeTests(unittest.TestCase):
    def test_fires_on_audiopad(self):
        self.assertIn("api_broken_node", graph_lint.fired_api(USES_AUDIOPAD))

    def test_silent_on_the_workaround(self):
        self.assertNotIn("api_broken_node", graph_lint.fired_api(USES_EMPTYAUDIO_CONCAT))

    def test_finding_names_the_replacement(self):
        findings = graph_lint.api_broken_node(USES_AUDIOPAD)
        self.assertTrue(any("EmptyAudio" in f.detail for f in findings))


class ByteDanceGlobalPitchTests(unittest.TestCase):
    def test_fires_when_two_characters_share_a_pitched_node(self):
        self.assertIn("api_bytedance_global_pitch_multivoice",
                      graph_lint.fired_api(BYTEDANCE_GLOBAL_PITCH))

    def test_silent_on_a_single_character_pass(self):
        self.assertNotIn("api_bytedance_global_pitch_multivoice",
                         graph_lint.fired_api(BYTEDANCE_ONE_CHARACTER))

    def test_silent_when_pitch_is_neutral(self):
        graph = {"1": dict(BYTEDANCE_GLOBAL_PITCH["1"])}
        graph["1"]["inputs"] = dict(graph["1"]["inputs"], pitch_rate=0)
        self.assertNotIn("api_bytedance_global_pitch_multivoice", graph_lint.fired_api(graph))


class ByteDanceReferenceTests(unittest.TestCase):
    def test_flags_every_audio_reference_render(self):
        self.assertIn("api_bytedance_reference_unverified",
                      graph_lint.fired_api(BYTEDANCE_AUDIO_REFERENCE))

    def test_silent_in_text_only_mode(self):
        self.assertNotIn("api_bytedance_reference_unverified",
                         graph_lint.fired_api(BYTEDANCE_ONE_CHARACTER))

    def test_finding_points_at_the_verifier(self):
        findings = graph_lint.api_bytedance_reference_unverified(BYTEDANCE_AUDIO_REFERENCE)
        self.assertTrue(any("dialogue_receipt" in f.detail for f in findings))


class RegistryHygieneTests(unittest.TestCase):
    def test_every_api_detector_is_silent_on_an_empty_graph(self):
        for name, detector in graph_lint.API_DETECTORS.items():
            self.assertEqual(detector({}), [], name)

    def test_every_api_detector_survives_a_malformed_graph(self):
        junk = {"1": None, "2": {"class_type": "LoadAudio"}, "3": {"class_type": "AudioPad", "inputs": None}}
        for name, detector in graph_lint.API_DETECTORS.items():
            detector(junk)  # must not raise

    def test_every_api_detector_fires_on_at_least_one_fixture(self):
        """No detector may pass by never being exercised."""
        fixtures = [CLONE_WRONG_SLOT, FISH_WRONG_VOICES, USES_AUDIOPAD,
                    BYTEDANCE_GLOBAL_PITCH, BYTEDANCE_AUDIO_REFERENCE]
        seen = set()
        for fixture in fixtures:
            seen |= graph_lint.fired_api(fixture)
        self.assertEqual(set(graph_lint.API_DETECTORS) - seen, set())

    def test_archived_api_graphs_are_clean(self):
        """Forward gate: nothing in the archive may trip an API detector."""
        for path in graph_lint.api_graph_paths():
            api = graph_lint.load_graph(path)
            fired = graph_lint.fired_api(api)
            self.assertEqual(fired, set(), "{0}: {1}".format(os.path.basename(path), fired))


if __name__ == "__main__":
    unittest.main()
