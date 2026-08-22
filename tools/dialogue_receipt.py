#!/usr/bin/env python3
"""Check a VO stem's *spoken content* against the scene script and emit a receipt.

Usage:
    python tools/dialogue_receipt.py <scene.json> <words.json> [--json out.json]

``scene.json`` is the authored scene (see ``docs/scenes/``). ``words.json`` is a
word-level diarized transcript of the rendered VO, as produced by
``ElevenLabsSpeechToText`` with ``model.diarize=true`` and
``model.timestamps_granularity="word"`` — save output slot 2 with ``SaveText``.

WHY THIS TOOL EXISTS (2026-08-22, session 4)
--------------------------------------------
``audition_receipt.py`` measures the *container*: sample rate, duration, LUFS,
track presence. Every one of those checks passed green on two VO stems the
Director rejected by ear within seconds:

1. A stem that contained a **fourth line nobody asked for** — ByteDance in
   ``audio reference`` mode reproduces the reference clip's dialogue *content*,
   not just its timbre, so a multi-line reference re-speaks lines the prompt
   never requested. Mixed under the real line, it read as two men talking over
   each other. 48 kHz, 9.840 s, contract-clean, completely broken.
2. A stem where one character's two sentences were separated by a gap long
   enough to run into the next character's cue.

Duration and sample rate cannot see either defect. Both are mechanically
detectable from a diarized transcript, which is what this tool checks.

This tool MEASURES; it does not fix. A failing check is a finding, not a bug in
the tool: report it, do not tune the thresholds to make it green. Exit 0 when
every check passes, 1 when any fails — so it can gate a render.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

#: Words are compared with punctuation and case stripped: a TTS engine's comma
#: placement is not a content defect, and the transcriber's punctuation is its
#: own guess. Apostrophes are KEPT — "cant" and "can't" are the same word but
#: dropping the mark makes diffs unreadable in a receipt.
_PUNCT = re.compile(r"[^a-z0-9']+")

#: Default budgets. Overridable per scene AND per line; every one of these traces
#: to a defect the Director caught by ear, not to a standard.
#:
#: The global default is deliberately loose: a comma pause inside a line is
#: normal delivery, not a defect, and a tool that flags every one of them is
#: noise. Where the Director has SPECIFIED the phrasing ("there's no pause in
#: between"), that intent belongs on the line as ``max_gap_s`` — the script is
#: where direction is recorded, not a global knob.
DEFAULT_MAX_GAP_WITHIN_LINE_S = 0.5
DEFAULT_MIN_GAP_BETWEEN_SPEAKERS_S = 0.0
DEFAULT_CLIP_DURATION_S = 10.062


def normalize(text: str) -> list[str]:
    """Split to comparable word tokens."""
    return [w for w in _PUNCT.sub(" ", (text or "").lower()).split() if w]


def load_words(path: str) -> list[dict]:
    """Read a diarized word list from disk. See :func:`normalize_words`."""
    with open(path, "r", encoding="utf-8") as handle:
        return normalize_words(json.load(handle))


def normalize_words(raw) -> list[dict]:
    """Coerce whatever the node emitted into the internal word shape.

    Accepts a bare list, or an object with a ``words`` key. Non-word entries
    (``type`` of ``spacing``/``audio_event``) are dropped — they carry no text
    to match and their timings would corrupt the gap measurements. Already-
    normalized input passes through unchanged, so callers may hand
    :func:`check_dialogue` raw node JSON without a conversion step.
    """
    words = raw if isinstance(raw, list) else raw.get("words", [])
    out = []
    for entry in words:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") not in (None, "word"):
            continue
        text = normalize(entry.get("text", ""))
        if not text:
            continue
        out.append({
            "text": text[0] if len(text) == 1 else " ".join(text),
            "tokens": text,
            "start": float(entry.get("start", 0.0)),
            "end": float(entry.get("end", 0.0)),
            "speaker": entry.get("speaker_id") or entry.get("speaker"),
        })
    return out


def _flatten(words: list[dict]) -> list[dict]:
    """One entry per token, so a transcriber that fuses two words still aligns."""
    flat = []
    for word in words:
        tokens = word["tokens"]
        span = (word["end"] - word["start"]) / max(len(tokens), 1)
        for i, token in enumerate(tokens):
            flat.append({
                "text": token,
                "start": word["start"] + i * span,
                "end": word["start"] + (i + 1) * span,
                "speaker": word["speaker"],
            })
    return flat


def align(scene_lines: list[dict], words: list[dict]) -> tuple[list[dict], list[dict]]:
    """Match each scripted line to a consecutive run of transcript tokens.

    Returns ``(matched, unconsumed)``. A line that cannot be found anywhere at or
    after the cursor is returned with ``found=False`` rather than raising — a
    missing line is a finding, and the receipt should report the others too.

    ``unconsumed`` is every token no scripted line claimed. That list is the
    detector for content the model invented: it is how the phantom fourth line
    would have been caught before the mix.
    """
    flat = _flatten(words)
    cursor = 0
    matched: list[dict] = []
    claimed: set[int] = set()

    for line in scene_lines:
        want = normalize(line.get("text", ""))
        hit = None
        if want:
            for start in range(cursor, len(flat) - len(want) + 1):
                if all(flat[start + i]["text"] == want[i] for i in range(len(want))):
                    hit = start
                    break
        if hit is None:
            matched.append({
                "speaker": line.get("speaker"),
                "text": line.get("text"),
                "found": False,
            })
            continue
        run = flat[hit:hit + len(want)]
        claimed.update(range(hit, hit + len(want)))
        speakers = [w["speaker"] for w in run if w["speaker"] is not None]
        # widest gap between consecutive tokens inside the line -- the pause check
        gaps = [run[i + 1]["start"] - run[i]["end"] for i in range(len(run) - 1)]
        matched.append({
            "speaker": line.get("speaker"),
            "text": line.get("text"),
            "max_gap_s": line.get("max_gap_s"),
            "found": True,
            "start": round(run[0]["start"], 3),
            "end": round(run[-1]["end"], 3),
            "diarized_speaker": max(set(speakers), key=speakers.count) if speakers else None,
            "max_internal_gap_s": round(max(gaps), 3) if gaps else 0.0,
        })
        cursor = hit + len(want)

    unconsumed = [w for i, w in enumerate(flat) if i not in claimed]
    return matched, unconsumed


def check_dialogue(scene: dict, words: list[dict], only_speaker: str | None = None) -> dict:
    """Return {'checks': [...], 'measured': {...}} — never raises on bad input.

    ``only_speaker`` narrows the contract to one character's lines, which is how
    a per-character STEM is checked. This is the mode that catches invented
    speech: a VOICE stem is supposed to carry VOICE's lines and *silence* where
    the other character talks, so any other words in it are a defect. Checking a
    stem against the whole scene hides exactly that bug — it did, on 2026-08-22,
    and the phantom line reached the Director.
    """
    checks: list[dict] = []
    measured: dict = {}

    def record(name, ok, detail, traces_to):
        checks.append({"check": name, "ok": bool(ok), "detail": detail, "traces_to": traces_to})

    words = normalize_words(words)
    lines = scene.get("lines", []) or []
    if only_speaker is not None:
        lines = [ln for ln in lines if ln.get("speaker") == only_speaker]
        measured["only_speaker"] = only_speaker
    max_gap = float(scene.get("max_gap_within_line_s", DEFAULT_MAX_GAP_WITHIN_LINE_S))
    min_turn_gap = float(scene.get("min_gap_between_speakers_s", DEFAULT_MIN_GAP_BETWEEN_SPEAKERS_S))
    clip_s = float(scene.get("clip_duration_s", DEFAULT_CLIP_DURATION_S))

    matched, unconsumed = align(lines, words)
    measured["lines"] = matched
    measured["unconsumed_words"] = [w["text"] for w in unconsumed]

    # --- every scripted line is present, in order ----------------------------
    for i, line in enumerate(matched):
        record(
            "line_present:{0}:{1}".format(i, line.get("speaker")),
            line.get("found"),
            line.get("text") if line.get("found") else "NOT FOUND: " + str(line.get("text")),
            "the scene script is the contract",
        )

    found = [m for m in matched if m.get("found")]

    # --- nothing the script did not ask for ----------------------------------
    #: The ByteDance reference-bleed trap. An audio reference carrying dialogue
    #: makes the model re-speak lines the prompt omitted; mixed against the real
    #: take it reads as overlapping voices.
    record(
        "no_invented_speech",
        not unconsumed,
        "clean" if not unconsumed else
        "{0} unscripted word(s): {1}".format(len(unconsumed), " ".join(w["text"] for w in unconsumed[:12])),
        "trap: ByteDance audio-reference reproduces the reference's dialogue content",
    )

    # --- lines do not overlap each other -------------------------------------
    overlaps = []
    for a, b in zip(found, found[1:]):
        if b["start"] < a["end"]:
            overlaps.append("{0!r} overlaps {1!r} by {2:.2f}s".format(
                a["text"][:24], b["text"][:24], a["end"] - b["start"]))
    record(
        "no_overlap",
        not overlaps,
        "clean" if not overlaps else "; ".join(overlaps),
        "two characters talking over each other is the worst-sounding failure",
    )

    # --- a character's own line does not straggle ----------------------------
    #: The pause defect: ByteDance rendered "Not bad." and "Can't complain."
    #: far enough apart that the second half ran into the next character's cue.
    straggles = []
    for line in found:
        budget = line.get("max_gap_s")
        budget = max_gap if budget is None else float(budget)
        if line["max_internal_gap_s"] > budget:
            straggles.append("{0!r} holds {1:.2f}s mid-line (budget {2:.2f}s)".format(
                line["text"][:32], line["max_internal_gap_s"], budget))
    record(
        "no_internal_straggle",
        not straggles,
        "clean" if not straggles else "; ".join(straggles),
        "a mid-line pause eats the next character's slot",
    )

    # --- turn-taking gaps ----------------------------------------------------
    tight = []
    for a, b in zip(found, found[1:]):
        if a.get("speaker") != b.get("speaker"):
            gap = b["start"] - a["end"]
            if gap < min_turn_gap:
                tight.append("{0}->{1} gap {2:.2f}s".format(a.get("speaker"), b.get("speaker"), gap))
    record(
        "turn_gaps",
        not tight,
        "clean" if not tight else "; ".join(tight),
        "scene pacing",
    )

    # --- casting: one voice per character, consistently ----------------------
    #: The defect that started session 4: the deep voice spoke BOTH characters'
    #: lines. Diarization sees one speaker where the script names two.
    cast: dict = {}
    for line in found:
        if line.get("diarized_speaker") is not None:
            cast.setdefault(line["speaker"], set()).add(line["diarized_speaker"])
    measured["casting"] = {k: sorted(v) for k, v in cast.items()}
    split = [k for k, v in cast.items() if len(v) > 1]
    record(
        "one_voice_per_character",
        not split,
        "clean" if not split else "{0} rendered by more than one voice".format(", ".join(split)),
        "trap: a character re-cast between renders is not a character",
    )

    all_ids = [next(iter(v)) for v in cast.values() if len(v) == 1]
    record(
        "characters_are_distinct",
        len(set(all_ids)) == len(all_ids),
        "{0} character(s) -> {1} distinct voice(s)".format(len(all_ids), len(set(all_ids))),
        "trap: pitch_rate is node-global, so one node cannot voice two characters",
    )

    # --- the whole exchange fits the clip ------------------------------------
    last = max((m["end"] for m in found), default=0.0)
    measured["speech_ends_s"] = round(last, 3)
    measured["clip_duration_s"] = clip_s
    record(
        "fits_clip",
        last <= clip_s,
        "speech ends {0:.3f}s, clip is {1:.3f}s".format(last, clip_s),
        "choice F -- the dub may not outrun the picture",
    )

    return {"checks": checks, "measured": measured}


def render(result: dict) -> str:
    rows = []
    for check in result["checks"]:
        rows.append("| {0} | `{1}` | {2} | {3} |".format(
            "PASS" if check["ok"] else "FAIL",
            check["check"], check["detail"], check["traces_to"]))
    passed = sum(1 for c in result["checks"] if c["ok"])
    head = "{0}/{1} checks pass".format(passed, len(result["checks"]))
    return head + "\n" + "\n".join(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", help="authored scene JSON")
    parser.add_argument("words", help="diarized word-timestamp JSON from ElevenLabsSpeechToText")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--only-speaker", dest="only_speaker", default=None,
                        help="check a per-character STEM: narrow the contract to this "
                             "character's lines, so any other speech in the stem fails "
                             "no_invented_speech")
    args = parser.parse_args(argv)

    with open(args.scene, "r", encoding="utf-8") as handle:
        scene = json.load(handle)
    result = check_dialogue(scene, load_words(args.words), only_speaker=args.only_speaker)

    print(render(result))
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
    return 0 if all(c["ok"] for c in result["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
