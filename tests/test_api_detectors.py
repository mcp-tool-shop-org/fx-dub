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
                    BYTEDANCE_GLOBAL_PITCH, BYTEDANCE_AUDIO_REFERENCE,
                    LIPSYNC_UNPINNED, LIPSYNC_REMAP, SAVEVIDEO_CODEC_ENCODING]
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



# --- picture stage (session 5, 2026-08-23) ---------------------------------------

#: THE NEAR-MISS. speaker_selection defaults to "default" ("let the model decide").
#: Submitted like this the job COMPLETES, returns a correctly-framed 832x480 MP4 at
#: the right duration, and passes every container check we own -- with whichever
#: face the model chose doing the talking. The in-app agent refused to build this
#: because its tool surface could not address the coordinate fields, which is the
#: only reason it was never submitted.
LIPSYNC_UNPINNED = {
    "1": {"class_type": "LoadVideo", "inputs": {"file": "clip.mp4"}},
    "2": {"class_type": "LoadAudio", "inputs": {"audio": "mac.flac"}},
    "3": {"class_type": "SyncLipSyncNode",
          "inputs": {"video": ["1", 0], "audio": ["2", 0], "seed": 42,
                     "model": "sync-3", "model.sync_mode": "silence"}},
}

#: SUCCEEDED: job 4b2339b4-804a-42aa-8198-e2bf89877803, mouth on the named face.
LIPSYNC_PINNED = {
    "1": {"class_type": "LoadVideo", "inputs": {"file": "clip.mp4"}},
    "2": {"class_type": "LoadAudio", "inputs": {"audio": "mac.flac"}},
    "3": {"class_type": "SyncLipSyncNode",
          "inputs": {"video": ["1", 0], "audio": ["2", 0], "seed": 42,
                     "model": "sync-3", "model.sync_mode": "silence",
                     "model.speaker_selection": "coordinates",
                     "model.speaker_frame": 60,
                     "model.speaker_x": 348, "model.speaker_y": 122}},
}

#: remap time-stretches the PICTURE to the audio length. bounce and loop resize it
#: too. Only "silence" leaves the delivered duration alone.
LIPSYNC_REMAP = {
    "3": {"class_type": "SyncLipSyncNode",
          "inputs": {"video": ["1", 0], "audio": ["2", 0], "seed": 42,
                     "model": "sync-3", "model.sync_mode": "remap",
                     "model.speaker_selection": "coordinates",
                     "model.speaker_x": 348, "model.speaker_y": 122}},
}

#: CRASHED local pre-flight: "candidate.toLowerCase is not a function", no verdict
#: at all. codec.encoding's options are objects, not strings.
SAVEVIDEO_CODEC_ENCODING = {
    "4": {"class_type": "SaveVideo",
          "inputs": {"video": ["3", 0], "filename_prefix": "out",
                     "format": "mp4", "codec": "h264", "codec.encoding": "auto"}},
}

#: VALIDATED clean.
SAVEVIDEO_PLAIN = {
    "4": {"class_type": "SaveVideo",
          "inputs": {"video": ["3", 0], "filename_prefix": "out",
                     "format": "mp4", "codec": "h264"}},
}


class LipsyncSpeakerTests(unittest.TestCase):
    def test_red_on_unpinned_speaker(self):
        self.assertTrue(graph_lint.api_lipsync_unpinned_speaker(LIPSYNC_UNPINNED))

    def test_silent_on_pinned_speaker(self):
        self.assertEqual([], graph_lint.api_lipsync_unpinned_speaker(LIPSYNC_PINNED))

    def test_red_when_coordinates_selected_but_absent(self):
        graph = {"3": {"class_type": "SyncLipSyncNode",
                       "inputs": {"video": ["1", 0], "audio": ["2", 0], "seed": 42,
                                  "model": "sync-3",
                                  "model.speaker_selection": "coordinates"}}}
        self.assertTrue(graph_lint.api_lipsync_unpinned_speaker(graph))

    def test_auto_detect_is_not_good_enough(self):
        """auto-detect follows the ACTIVE speaker -- useless when the speaker is off-frame."""
        graph = {"3": {"class_type": "SyncLipSyncNode",
                       "inputs": {"model": "sync-3",
                                  "model.speaker_selection": "auto-detect"}}}
        self.assertTrue(graph_lint.api_lipsync_unpinned_speaker(graph))


class LipsyncSyncModeTests(unittest.TestCase):
    def test_red_on_remap(self):
        self.assertTrue(graph_lint.api_lipsync_resizing_sync_mode(LIPSYNC_REMAP))

    def test_silent_on_silence(self):
        self.assertEqual([], graph_lint.api_lipsync_resizing_sync_mode(LIPSYNC_PINNED))

    def test_cut_off_is_allowed(self):
        """cut_off trims rather than resamples; it is the cheap probe mode."""
        graph = {"3": {"class_type": "SyncLipSyncNode",
                       "inputs": {"model": "sync-3", "model.sync_mode": "cut_off"}}}
        self.assertEqual([], graph_lint.api_lipsync_resizing_sync_mode(graph))


class SaveVideoCodecTests(unittest.TestCase):
    def test_red_on_codec_encoding(self):
        self.assertTrue(graph_lint.api_savevideo_codec_encoding(SAVEVIDEO_CODEC_ENCODING))

    def test_silent_without_it(self):
        self.assertEqual([], graph_lint.api_savevideo_codec_encoding(SAVEVIDEO_PLAIN))


if __name__ == "__main__":
    unittest.main()
