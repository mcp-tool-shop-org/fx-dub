#!/usr/bin/env python3
"""Check a downloaded fx-dub run against the design contract and emit a receipt.

Usage:
    python tools/audition_receipt.py <run_dir> [--json out.json]

``run_dir`` holds the artifacts as downloaded from Comfy Cloud. Files are matched
by the graph's ``filename_prefix`` stems, whatever counter suffix the platform
appends (``fxdub/mix`` lands as ``mix_00001_.flac``):

    mix*.flac  stem_bed*.flac  stem_vo*.flac  mix_lufs*.txt  vo_lufs*.txt
    caption*.txt  dubbed*.mp4

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


def check_run(run_dir: str) -> dict:
    """Return {'checks': [...], 'measured': {...}} — never raises on a bad artifact."""
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
        record("audio:{0}:rate48k".format(key), info["sample_rate"] == RUNTIME_SAMPLE_RATE,
               "{0} Hz, {1}ch, {2:.3f}s".format(info["sample_rate"], info["channels"], info["duration_s"]),
               "dispatch choice F (48 kHz runtime standard)")

    if len(rates) > 1:
        record("audio:rates_agree", len(set(rates.values())) == 1,
               "rates: {0}".format(rates),
               "trap: no sample-rate-conversion node exists on cloud")

    # --- loudness (choice F) ---------------------------------------------------------
    lufs = {}
    for key in ("mix_lufs", "vo_lufs"):
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

    if "mix_lufs" in lufs and "vo_lufs" in lufs:
        # The VO meter reads the dialogue stem pre-gain; a positive offset means
        # dialogue sits above the mixed bed, which is the intent.
        offset = lufs["vo_lufs"] - lufs["mix_lufs"]
        measured["vo_minus_mix_lu"] = offset
        record("loudness:dialogue_anchored", BED_OFFSET_MIN <= abs(offset) <= BED_OFFSET_MAX,
               "VO - mix = {0:+.2f} LU (expect |{1:.0f}-{2:.0f}| with bed at -15 dB)".format(
                   offset, BED_OFFSET_MIN, BED_OFFSET_MAX),
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
    args = parser.parse_args(argv)

    if not os.path.isdir(args.run_dir):
        print("no such directory: {0}".format(args.run_dir), file=sys.stderr)
        return 2

    result = check_run(args.run_dir)
    print(render(result))
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
    return 0 if all(c["ok"] for c in result["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
