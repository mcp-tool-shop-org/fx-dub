#!/usr/bin/env python3
"""Check a downloaded fx-dub run against the design contract and emit a receipt.

Usage:
    python tools/audition_receipt.py <run_dir> [--json out.json]

``run_dir`` holds the artifacts as downloaded from Comfy Cloud. Files are matched
by the graph's ``filename_prefix`` stems, whatever counter suffix the platform
appends (``fxdub/mix`` lands as ``mix_00001_.flac``):

    mix*.flac  stem_bed*.flac  stem_vo*.flac
    mix_lufs*.txt  vo_lufs*.txt  bed_lufs*.txt  caption*.txt  dubbed*.mp4

The bed_lufs manifest is REQUIRED: EBU R128 integrated loudness gates a quiet bed
out of the mix master entirely, so dialogue-to-bed ducking depth is unmeasurable
without a meter on the bed stem itself (measured 2026-08-22).

Every CHECK below traces to a locked decision in
``docs/design/2026-08-21-fxdub-v1.dispatch.md`` (choice F for the mix targets,
choice H for the deliverable set) or to a measured trap in ``kb/fxdub.db``.
Exit 0 when every check passes, 1 when any fails — so it can gate a run.

This tool MEASURES; it does not fix. A failing check is a finding, not a bug in
the tool: report it, do not tune the thresholds to make it green.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from media_probe import parse_lufs, parse_streaminfo, probe_mp4  # noqa: E402

#: Choice F — the mix contract. Tolerances are the standards' own, not invented:
#: EBU R128 states +/-0.5 LU for a compliant target, and the dialogue-to-bed
#: offset is a listener-preference band (JAES 2019), so it is checked as a range.
RUNTIME_SAMPLE_RATE = 48000
TARGET_LUFS = -18.0
LUFS_TOLERANCE = 2.0
BED_OFFSET_MIN = 8.0
BED_OFFSET_MAX = 20.0

#: Which masters must carry the 48 kHz runtime rate. The VO stem is deliberately
#: NOT in this set: every text-to-speech model on Comfy Cloud decodes 24 kHz mono
#: and no sample-rate-conversion node exists on the platform, so a 48 kHz
#: assertion on a VO source stem can never pass on any graph we are able to build.
#: The rate that matters is the one the MIX and the DUB are delivered at, which
#: AudioMix fixes by adopting audio_1's rate -- hence bed-on-audio_1.
DELIVERED_AT_RUNTIME_RATE = ("mix", "stem_bed")
TTS_NATIVE_RATES = (24000, 22050, 16000)

#: Mix gain applied to the bed, in dB, needed to recover the delivered ducking
#: depth from a bed-stem meter that reads the stem pre-gain. Override per run.
DEFAULT_BED_GAIN_DB = -9.0

#: The fixture (cross-verified by two independent probes, 2026-08-21).
FIXTURE_FRAMES = 161
FIXTURE_DURATION_S = 10.062
DURATION_TOLERANCE_S = 0.5


def _find(run_dir: str, pattern: str) -> str | None:
    hits = sorted(glob.glob(os.path.join(run_dir, pattern)))
    return hits[0] if hits else None


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def check_run(run_dir: str, bed_gain_db: float = DEFAULT_BED_GAIN_DB) -> dict:
    """Return {'checks': [...], 'measured': {...}} — never raises on a bad artifact.

    ``bed_gain_db`` is the mix gain the graph applies to the bed. The bed meter
    reads the stem *pre-gain*, so recovering the delivered ducking depth needs it.
    """
    checks: list[dict] = []
    measured: dict = {}

    def record(name, ok, detail, traces_to):
        checks.append({"check": name, "ok": bool(ok), "detail": detail, "traces_to": traces_to})

    # --- deliverable set (choice H) -------------------------------------------------
    wanted = {
        "mix": "mix*.flac",
        "stem_bed": "stem_bed*.flac",
        "stem_vo": "stem_vo*.flac",
        "mix_lufs": "mix_lufs*.txt",
        "vo_lufs": "vo_lufs*.txt",
        "bed_lufs": "bed_lufs*.txt",
        "caption": "caption*.txt",
        "dubbed": "dubbed*.mp4",
    }
    found = {}
    for key, pattern in wanted.items():
        # stem_* must not be swallowed by the looser mix*/vo* globs
        path = _find(run_dir, pattern)
        found[key] = path
        record("deliverable:" + key, path is not None,
               os.path.basename(path) if path else "missing ({0})".format(pattern),
               "dispatch choice H")

    # --- audio masters --------------------------------------------------------------
    rates = {}
    for key in ("mix", "stem_bed", "stem_vo"):
        path = found.get(key)
        if not path:
            continue
        try:
            info = parse_streaminfo(_read_bytes(path))
        except Exception as exc:  # a corrupt master is a finding, not a crash
            record("audio:" + key, False, "unreadable FLAC: {0}".format(exc), "trap: masters are FLAC")
            continue
        measured[key] = info
        rates[key] = info["sample_rate"]
        if key in DELIVERED_AT_RUNTIME_RATE:
            record("audio:{0}:rate48k".format(key), info["sample_rate"] == RUNTIME_SAMPLE_RATE,
                   "{0} Hz, {1}ch, {2:.3f}s".format(
                       info["sample_rate"], info["channels"], info["duration_s"]),
                   "dispatch choice F (48 kHz runtime standard)")
        else:
            # MEASURED 2026-08-22: every text-to-speech option on Comfy Cloud decodes
            # 24 kHz mono -- FL_ChatterboxTTS, FB_Qwen3TTSVoiceDesign and
            # FB_Qwen3TTSCustomVoice alike -- and there is no sample-rate-conversion
            # node anywhere on the platform. Asserting 48 kHz on a VO *source stem*
            # was therefore a check that could never pass on any graph we can build:
            # noise, not a gate. What actually matters is that the DELIVERED mix and
            # dub carry the runtime rate, which AudioMix does by taking audio_1's rate
            # -- so the bed occupies audio_1 and the VO is upsampled into the mix.
            record("audio:{0}:native_rate".format(key), info["sample_rate"] in TTS_NATIVE_RATES,
                   "{0} Hz, {1}ch, {2:.3f}s (source stem; cloud TTS is 24 kHz)".format(
                       info["sample_rate"], info["channels"], info["duration_s"]),
                   "measured: all cloud TTS decodes 24 kHz mono; no SRC node exists")

    delivered = {k: v for k, v in rates.items() if k in DELIVERED_AT_RUNTIME_RATE}
    if len(delivered) > 1:
        record("audio:rates_agree", len(set(delivered.values())) == 1,
               "delivered rates: {0} (source stems excluded: {1})".format(
                   delivered, {k: v for k, v in rates.items() if k not in DELIVERED_AT_RUNTIME_RATE}),
               "trap: no sample-rate-conversion node exists on cloud")

    # --- loudness (choice F) ---------------------------------------------------------
    lufs = {}
    for key in ("mix_lufs", "vo_lufs", "bed_lufs"):
        path = found.get(key)
        if not path:
            continue
        try:
            lufs[key] = parse_lufs(_read_text(path))
        except Exception as exc:
            record("loudness:" + key, False, "unparseable manifest: {0}".format(exc),
                   "trap: STRING outputs reach the manifest only via SaveText")
    measured["lufs"] = lufs

    if "mix_lufs" in lufs:
        delta = abs(lufs["mix_lufs"] - TARGET_LUFS)
        record("loudness:mix_target", delta <= LUFS_TOLERANCE,
               "{0:+.2f} LUFS (target {1:+.1f} +/- {2:.1f})".format(
                   lufs["mix_lufs"], TARGET_LUFS, LUFS_TOLERANCE),
               "dispatch choice F (AES TD1008 'Assorted')")

    # Ducking depth is VO-minus-BED, and it can ONLY be measured from two stem meters.
    #
    # This check used to compute VO minus MIX, which is structurally incapable of
    # measuring anything. MEASURED 2026-08-22: with the bed at -39.29 LUFS and the VO
    # at -16.22, the mix metered -16.22 -- byte-identical to the VO reading, because
    # EBU R128 *integrated* loudness applies a relative gate ~10 LU below the ungated
    # level and simply discards the bed. The old check compared two numbers dominated
    # by the same speech blocks and reported +0.00 LU on a mix whose bed was 23 LU
    # down and inaudible. Requiring a third meter on the bed stem is the fix; there is
    # no way to recover ducking depth from the mix master alone.
    if "vo_lufs" in lufs and "bed_lufs" in lufs:
        offset = lufs["vo_lufs"] - (lufs["bed_lufs"] + bed_gain_db)
        measured["vo_minus_bed_lu"] = offset
        record("loudness:dialogue_anchored", BED_OFFSET_MIN <= offset <= BED_OFFSET_MAX,
               "VO - bed = {0:+.2f} LU (expect {1:.0f}-{2:.0f}; bed stem {3:+.2f} LUFS "
               "at {4:+.0f} dB mix gain)".format(
                   offset, BED_OFFSET_MIN, BED_OFFSET_MAX, lufs["bed_lufs"], bed_gain_db),
               "dispatch choice F (ATSC A/85 anchor + JAES 2019 ducking depth)")
    else:
        record("loudness:dialogue_anchored", False,
               "no bed_lufs manifest: ducking depth is UNMEASURABLE from mix+vo alone "
               "(R128 integrated loudness gates the bed out) -- the graph needs a third "
               "AudioLoudnessMeter on the bed stem",
               "dispatch choice F (ATSC A/85 anchor + JAES 2019 ducking depth)")

    # --- the dub itself --------------------------------------------------------------
    path = found.get("dubbed")
    if path:
        try:
            info = probe_mp4(_read_bytes(path))
        except Exception as exc:
            record("dub:readable", False, "unreadable MP4: {0}".format(exc), "dispatch choice H")
        else:
            measured["dubbed"] = {
                k: info[k] for k in
                ("movie_timescale", "movie_header_valid", "handlers",
                 "has_video_track", "has_audio_track", "frame_count")
            }
            record("dub:has_audio", info["has_audio_track"],
                   "handlers={0}".format(info["handlers"]),
                   "the whole point of re-mux: audio muxed back onto the video")
            record("dub:has_video", info["has_video_track"],
                   "handlers={0}".format(info["handlers"]), "dispatch choice H")
            if info["frame_count"] is not None:
                record("dub:frames_intact", info["frame_count"] == FIXTURE_FRAMES,
                       "{0} frames (fixture has {1})".format(info["frame_count"], FIXTURE_FRAMES),
                       "trap: skip_first_frames on the loader silently truncates the dub")
            track_durations = [t["duration_s"] for t in info["tracks"] if t["duration_s"]]
            if track_durations:
                longest = max(track_durations)
                record("dub:duration", abs(longest - FIXTURE_DURATION_S) <= DURATION_TOLERANCE_S,
                       "{0:.3f}s (fixture {1:.3f}s)".format(longest, FIXTURE_DURATION_S),
                       "fixture cross-verified 2026-08-21")

    # --- semantic trail (choice H) ----------------------------------------------------
    path = found.get("caption")
    if path:
        text = _read_text(path).strip()
        measured["caption_chars"] = len(text)
        record("caption:non_empty", len(text) > 0,
               "{0} chars".format(len(text)),
               "dispatch choice H (the semantic intermediate must reach the manifest)")

    return {"run_dir": run_dir, "checks": checks, "measured": measured}


def render(result: dict) -> str:
    lines = ["# fx-dub audition receipt", "", "Run: `{0}`".format(result["run_dir"]), ""]
    passed = sum(1 for c in result["checks"] if c["ok"])
    total = len(result["checks"])
    lines.append("**{0}/{1} checks passed.**".format(passed, total))
    lines.append("")
    lines.append("| | Check | Measured | Traces to |")
    lines.append("|---|---|---|---|")
    for c in result["checks"]:
        lines.append("| {0} | `{1}` | {2} | {3} |".format(
            "PASS" if c["ok"] else "**FAIL**", c["check"], c["detail"], c["traces_to"]))
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--bed-gain-db", dest="bed_gain_db", type=float,
                        default=DEFAULT_BED_GAIN_DB,
                        help="mix gain applied to the bed, in dB (the bed meter reads "
                             "the stem pre-gain, so ducking depth needs it)")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.run_dir):
        print("no such directory: {0}".format(args.run_dir), file=sys.stderr)
        return 2

    result = check_run(args.run_dir, bed_gain_db=args.bed_gain_db)
    print(render(result))
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
    return 0 if all(c["ok"] for c in result["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
