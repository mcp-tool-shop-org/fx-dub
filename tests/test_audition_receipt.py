"""The audition receipt checker — and proof each check can go RED.

The receipt gates the first real fx-dub run, so the tests build synthetic runs on
disk (good and deliberately broken) and assert the checker's verdict. A checker
that cannot fail is theater; ``test_every_check_can_fail`` enforces that every
check name emitted on a good run also appears failing somewhere in this file's
broken runs.
"""

from __future__ import annotations

import os
import struct
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audition_receipt  # noqa: E402
from flac_info import build_streaminfo  # noqa: E402
from media_probe import parse_lufs, probe_mp4  # noqa: E402


def _atom(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body) + 8) + kind + body


def make_mp4(frames=161, timescale=16384, duration=164864,
             handlers=(b"vide", b"soun"), movie_timescale=0) -> bytes:
    """A minimal ISO-BMFF skeleton carrying only the fields the probe reads.

    movie_timescale defaults to 0 on purpose: that is what the real audition
    fixture contains, and the probe must survive it.
    """
    mvhd = _atom(b"mvhd", bytes([0, 0, 0, 0]) + struct.pack(">II", 0, 0)
                 + struct.pack(">II", movie_timescale, 1000))
    body = mvhd
    for handler in handlers:
        mdhd = _atom(b"mdhd", bytes([0, 0, 0, 0]) + struct.pack(">II", 0, 0)
                     + struct.pack(">II", timescale, duration))
        hdlr = _atom(b"hdlr", bytes(8) + handler + bytes(12))
        body += _atom(b"trak", mdhd + hdlr)
    body += _atom(b"stsz", struct.pack(">III", 0, 0, frames))
    return _atom(b"ftyp", b"isom" + bytes(8)) + _atom(b"moov", body) + _atom(b"mdat", bytes(16))


def make_flac(sample_rate=48000, channels=2, seconds=10.0) -> bytes:
    return build_streaminfo(sample_rate, channels, 16, int(sample_rate * seconds))


def write_run(root, *, mix_rate=48000, bed_rate=48000, vo_rate=24000,
              mix_lufs=-18.1, vo_lufs=-14.0, bed_lufs=-17.2, bed_gain_db=-9.0,
              frames=161, handlers=(b"vide", b"soun"),
              track_duration=164864, caption="a rain-soaked street at night", omit=()):
    """Materialise a synthetic run directory; `omit` drops deliverables by key."""
    files = {
        "mix": ("mix_00001_.flac", make_flac(mix_rate)),
        "stem_bed": ("stem_bed_00001_.flac", make_flac(bed_rate)),
        "stem_vo": ("stem_vo_00001_.flac", make_flac(vo_rate, channels=2, seconds=5.8)),
        "mix_lufs": ("mix_lufs_00001_.txt",
                     "Integrated Loudness: {0} LUFS\n".format(mix_lufs).encode()),
        "vo_lufs": ("vo_lufs_00001_.txt",
                    "Integrated Loudness: {0} LUFS\n".format(vo_lufs).encode()),
        "bed_lufs": ("bed_lufs_00001_.txt",
                     "Integrated Loudness: {0} LUFS\n".format(bed_lufs).encode()),
        "caption": ("caption_00001_.txt", caption.encode()),
        "dubbed": ("dubbed_00001_.mp4",
                   make_mp4(frames=frames, handlers=handlers, duration=track_duration)),
    }
    for key, (name, blob) in files.items():
        if key in omit:
            continue
        with open(os.path.join(root, name), "wb") as handle:
            handle.write(blob)
    return root


def verdict(result):
    return {c["check"]: c["ok"] for c in result["checks"]}


class SyntheticFixtureTests(unittest.TestCase):
    """The fixture builders must themselves be trustworthy."""

    def test_mp4_skeleton_round_trips(self):
        info = probe_mp4(make_mp4())
        self.assertTrue(info["has_video_track"])
        self.assertTrue(info["has_audio_track"])
        self.assertEqual(info["frame_count"], 161)
        self.assertFalse(info["movie_header_valid"], "fixture models the timescale-0 file")
        self.assertAlmostEqual(max(t["duration_s"] for t in info["tracks"]), 10.062, places=2)

    def test_probe_rejects_non_mp4(self):
        with self.assertRaises(ValueError):
            probe_mp4(b"this is not a container at all")

    def test_lufs_parser(self):
        self.assertEqual(parse_lufs("Integrated Loudness: -12.32 LUFS"), -12.32)
        with self.assertRaises(ValueError):
            parse_lufs("loudness is fine, trust me")


class GoodRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        write_run(self.tmp.name)
        self.result = audition_receipt.check_run(self.tmp.name)

    def test_a_conforming_run_passes_every_check(self):
        failed = [c for c in self.result["checks"] if not c["ok"]]
        self.assertEqual([], failed, "conforming run should be all-green")

    def test_receipt_renders_with_traceability(self):
        text = audition_receipt.render(self.result)
        self.assertIn("audition receipt", text)
        self.assertIn("dispatch choice", text, "every check must cite what it traces to")

    def test_every_check_names_its_source(self):
        for check in self.result["checks"]:
            with self.subTest(check=check["check"]):
                self.assertTrue(check["traces_to"], "check has no traceability")


class RedGateTests(unittest.TestCase):
    """Each contract violation must be caught. These are the checks that matter."""

    def _run(self, **kwargs):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # bed_gain_db describes the GRAPH, not the artifacts, so it is threaded to
        # the checker rather than written into the run directory.
        bed_gain_db = kwargs.get("bed_gain_db", -9.0)
        write_run(tmp.name, **kwargs)
        return verdict(audition_receipt.check_run(tmp.name, bed_gain_db=bed_gain_db))

    def test_catches_wrong_sample_rate(self):
        v = self._run(mix_rate=44100)
        self.assertFalse(v["audio:mix:rate48k"])

    def test_catches_disagreeing_rates_across_stems(self):
        v = self._run(bed_rate=44100)
        self.assertFalse(v["audio:rates_agree"])

    def test_catches_loudness_off_target(self):
        v = self._run(mix_lufs=-9.0)
        self.assertFalse(v["loudness:mix_target"])

    def test_catches_dialogue_buried_in_the_bed(self):
        # VO -18.2, bed -17.2 at 0 dB gain => the dialogue sits BELOW the bed.
        v = self._run(vo_lufs=-18.2, bed_lufs=-17.2, bed_gain_db=0.0)
        self.assertFalse(v["loudness:dialogue_anchored"])

    def test_ducking_depth_is_unmeasurable_without_a_bed_meter(self):
        """R128 gates a quiet bed out of the mix master, so mix+vo cannot answer it.

        This is the defect that shipped in the first audition: the check read
        +0.00 LU on a mix whose bed was 23 LU down and inaudible. Absent a bed
        meter the honest verdict is FAIL, never a pass by omission.
        """
        v = self._run(omit=("bed_lufs",))
        self.assertFalse(v["loudness:dialogue_anchored"])

    def test_vo_stem_at_48k_from_elevenlabs_passes(self):
        """ElevenLabs emits 48 kHz; a check that punishes the upgrade is broken."""
        v = self._run(vo_rate=48000)
        self.assertTrue(v["audio:stem_vo:native_rate"])

    def test_vo_stem_at_a_rate_no_tts_produces_still_fails(self):
        v = self._run(vo_rate=32000)
        self.assertFalse(v["audio:stem_vo:native_rate"])

    def test_vo_stem_at_24k_is_not_a_failure(self):
        """Every cloud TTS decodes 24 kHz and no SRC node exists on the platform.

        Asserting 48 kHz on a VO *source* stem was a check no buildable graph
        could pass. What must hold is that the DELIVERED mix carries 48 kHz.
        """
        v = self._run(vo_rate=24000)
        self.assertTrue(v["audio:stem_vo:native_rate"])
        self.assertTrue(v["audio:rates_agree"])
        self.assertTrue(v["audio:mix:rate48k"])

    def test_catches_a_silent_dub(self):
        """The re-mux failing is the single worst outcome: video with no audio."""
        v = self._run(handlers=(b"vide",))
        self.assertFalse(v["dub:has_audio"])

    def test_catches_truncated_frames(self):
        v = self._run(frames=153)
        self.assertFalse(v["dub:frames_intact"])

    def test_catches_missing_deliverables(self):
        v = self._run(omit=("stem_vo", "caption"))
        self.assertFalse(v["deliverable:stem_vo"])
        self.assertFalse(v["deliverable:caption"])

    def test_catches_empty_caption(self):
        v = self._run(caption="")
        self.assertFalse(v["caption:non_empty"])

    def test_catches_a_video_less_dub(self):
        v = self._run(handlers=(b"soun",))
        self.assertFalse(v["dub:has_video"])

    def test_catches_wrong_dub_duration(self):
        """A dub whose length drifted from the source is a mux defect."""
        v = self._run(track_duration=16384 * 4)  # 4 s against a 10.06 s fixture
        self.assertFalse(v["dub:duration"])

    def test_every_check_can_fail(self):
        """No check may be structurally incapable of failing.

        Every axis the checker inspects gets a broken variant here. When a new
        check is added to audition_receipt.py, this test fails until a fixture
        that trips it is added — which is the point.
        """
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        write_run(tmp.name)
        good = {c["check"] for c in audition_receipt.check_run(tmp.name)["checks"]}

        broken = [
            # every rate wrong and mutually disagreeing, loudness far off target
            self._run(mix_rate=44100, bed_rate=22050, vo_rate=32000,
                      mix_lufs=-3.0, frames=1, caption=""),
            # dialogue buried in the bed (offset below the band)
            self._run(vo_lufs=-18.2, bed_lufs=-17.2, bed_gain_db=0.0),
            # ducking depth unmeasurable: no meter on the bed stem
            self._run(omit=("bed_lufs",)),
            # a VO stem at a rate no cloud TTS produces (44.1k is a music rate)
            self._run(vo_rate=44100),
            # the two mux catastrophes: no audio, and no video
            self._run(handlers=(b"vide",)),
            self._run(handlers=(b"soun",)),
            # length drift
            self._run(track_duration=16384 * 4),
            # nothing delivered at all
            self._run(omit=("mix", "stem_bed", "stem_vo", "mix_lufs",
                            "vo_lufs", "caption", "dubbed")),
        ]
        ever_failed = set()
        for v in broken:
            ever_failed |= {name for name, ok in v.items() if not ok}

        never_failing = good - ever_failed
        self.assertEqual(
            set(), never_failing,
            "these checks never go red and are therefore theater: {0}".format(sorted(never_failing)))


class CliTests(unittest.TestCase):
    def test_exit_code_zero_on_good_run(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        write_run(tmp.name)
        self.assertEqual(0, audition_receipt.main([tmp.name]))

    def test_exit_code_one_on_bad_run(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        write_run(tmp.name, handlers=(b"vide",))
        self.assertEqual(1, audition_receipt.main([tmp.name]))

    def test_exit_code_two_on_missing_directory(self):
        self.assertEqual(2, audition_receipt.main([os.path.join(REPO_ROOT, "no-such-run-dir")]))

    def test_json_export(self):
        import json
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        write_run(tmp.name)
        out = os.path.join(tmp.name, "receipt.json")
        audition_receipt.main([tmp.name, "--json", out])
        with open(out, encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertIn("checks", payload)
        self.assertIn("measured", payload)


if __name__ == "__main__":
    unittest.main()
