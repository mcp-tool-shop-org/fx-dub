"""The receipt tool — flac_info.parse_streaminfo.

Cloud audio claims are only measurements once the returned master's header has
been decoded locally (AGENTS.md operating rule 1: "verify, don't relay"). This
tests the decoder against synthetic FLAC headers constructed in-test, so no
binary fixtures enter the repo and the arithmetic is checked round-trip.

The two headers that matter to the project are exercised by name: the ACE-Step
1.0 SFX demo (44.1 kHz stereo) and the ChatterBox dialogue demo (24 kHz mono) —
the pair that proved the mixed-rate / mixed-channel trap in the v1 ledger.
"""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import flac_info  # noqa: E402
from flac_info import build_streaminfo, parse_streaminfo  # noqa: E402


class ParseStreaminfoTests(unittest.TestCase):
    def test_cd_quality_round_trip(self):
        data = build_streaminfo(44100, 2, 16, 441000)
        info = parse_streaminfo(data)
        self.assertEqual(44100, info["sample_rate"])
        self.assertEqual(2, info["channels"])
        self.assertEqual(16, info["bits_per_sample"])
        self.assertEqual(441000, info["total_samples"])
        self.assertAlmostEqual(10.0, info["duration_s"], places=9)

    def test_chatterbox_shaped_header(self):
        """24 kHz MONO 16-bit, 5.800 s — the measured cloud ChatterBox output."""
        info = parse_streaminfo(build_streaminfo(24000, 1, 16, 139200))
        self.assertEqual(24000, info["sample_rate"])
        self.assertEqual(1, info["channels"])
        self.assertEqual(16, info["bits_per_sample"])
        self.assertAlmostEqual(5.8, info["duration_s"], places=6)

    def test_ace_step_demo_shaped_header(self):
        """44.1 kHz stereo 16-bit, 9.938 s — the measured ACE-Step 1.0 SFX demo."""
        info = parse_streaminfo(build_streaminfo(44100, 2, 16, 438265))
        self.assertEqual(44100, info["sample_rate"])
        self.assertEqual(2, info["channels"])
        self.assertAlmostEqual(9.938, info["duration_s"], places=3)

    def test_48k_stereo_24bit(self):
        """The ACE-Step 1.5 production lane decodes at 48 kHz."""
        info = parse_streaminfo(build_streaminfo(48000, 2, 24, 48000 * 60))
        self.assertEqual(48000, info["sample_rate"])
        self.assertEqual(24, info["bits_per_sample"])
        self.assertAlmostEqual(60.0, info["duration_s"], places=9)

    def test_extreme_field_widths_round_trip(self):
        """8 channels and a 36-bit sample count exercise the packed-field masks."""
        total = (1 << 36) - 1
        info = parse_streaminfo(build_streaminfo(192000, 8, 32, total))
        self.assertEqual(192000, info["sample_rate"])
        self.assertEqual(8, info["channels"])
        self.assertEqual(32, info["bits_per_sample"])
        self.assertEqual(total, info["total_samples"])

    def test_block_sizes_and_md5_survive(self):
        md5 = bytes(range(16))
        info = parse_streaminfo(
            build_streaminfo(44100, 2, 16, 44100, min_block_size=1152,
                             max_block_size=4608, md5=md5))
        self.assertEqual(1152, info["min_block_size"])
        self.assertEqual(4608, info["max_block_size"])
        self.assertEqual(md5, info["md5"])

    def test_trailing_bytes_are_ignored(self):
        """A real file has frames after STREAMINFO; the decoder reads the header only."""
        data = build_streaminfo(44100, 2, 16, 441000) + os.urandom(4096)
        self.assertEqual(44100, parse_streaminfo(data)["sample_rate"])

    def test_returns_every_documented_key(self):
        info = parse_streaminfo(build_streaminfo(44100, 2, 16, 441000))
        for key in ("sample_rate", "channels", "bits_per_sample", "total_samples", "duration_s"):
            with self.subTest(key=key):
                self.assertIn(key, info)


class ParseStreaminfoRejectionTests(unittest.TestCase):
    def test_non_flac_bytes_raise_value_error(self):
        with self.assertRaises(ValueError):
            parse_streaminfo(b"RIFF\x00\x00\x00\x00WAVEfmt ")

    def test_empty_bytes_raise_value_error(self):
        with self.assertRaises(ValueError):
            parse_streaminfo(b"")

    def test_magic_only_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_streaminfo(flac_info.FLAC_MAGIC)

    def test_truncated_streaminfo_body_raises_value_error(self):
        data = build_streaminfo(44100, 2, 16, 441000)
        with self.assertRaises(ValueError):
            parse_streaminfo(data[:30])

    def test_wrong_first_block_type_raises_value_error(self):
        data = bytearray(build_streaminfo(44100, 2, 16, 441000))
        data[4] = 4  # VORBIS_COMMENT where STREAMINFO must be
        with self.assertRaises(ValueError):
            parse_streaminfo(bytes(data))

    def test_zero_sample_rate_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_streaminfo(build_streaminfo(0, 2, 16, 441000))

    def test_non_bytes_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_streaminfo("fLaC not bytes")


if __name__ == "__main__":
    unittest.main()
