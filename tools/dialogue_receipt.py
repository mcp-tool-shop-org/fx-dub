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

WHAT LIVES HERE vs IN ``fxdub.verify``
--------------------------------------
The alignment core is :mod:`fxdub.verify` — the declared public API — and this
module is one of its consumers. What stays here is everything that makes a
receipt a *video dub* receipt: the pause and turn-gap budgets (each traces to a
defect caught by ear on one specific clip, not to a standard), the overlap and
straggle checks, the clip fit, and the per-line receipt rendering.

**Building a tool on fx-dub? Import** :mod:`fxdub.verify`, not this module.
"""

from __future__ import annotations

import argparse
import json
import sys

# The alignment core lives in fxdub.verify — the DECLARED public API. This CLI is
# a consumer of it like any other, deliberately: a public surface the tool that
# ships it does not itself use is a second-class path, and it drifts. Everything
# below this import is what makes this receipt a *video dub* receipt — the
# budgets, the overlap and straggle checks, the clip fit. The medium-agnostic
# half is imported, never re-implemented.
try:  # package import: `fxdub.dialogue_receipt`
    from . import verify
except ImportError:  # direct script: `python tools/dialogue_receipt.py`
    import verify  # type: ignore[no-redef]

#: Re-exported from :mod:`fxdub.verify` — the same objects, not copies, so the
#: CLI and the public API cannot disagree about what a word is.
normalize = verify.normalize_text
normalize_words = verify.normalize_words

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


def load_words(path: str) -> list[dict]:
    """Read a diarized word list from disk and normalize it.

    The only IO in the content path. :func:`fxdub.verify.normalize_words`
    documents every transcript shape this accepts.
    """
    with open(path, "r", encoding="utf-8") as handle:
        return normalize_words(json.load(handle))


def align(scene_lines: list[dict], words: list[dict]) -> tuple[list[dict], list[dict]]:
    """Match each scripted line to a consecutive run of transcript tokens.

    A thin adapter over :func:`fxdub.verify.align_lines`, kept because it
    predates the public API and callers exist. It returns the older
    ``(matched, unconsumed)`` tuple; new code should call ``align_lines`` and use
    the :class:`~fxdub.verify.AlignResult` it returns, which names ``missing``
    and ``invented_words`` directly.
    """
    result = verify.align_lines(scene_lines, words)
    return result.matched, result.unconsumed


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

    def record_check(check):
        """Append a verdict the public API computed, in this receipt's row shape."""
        checks.append(check.as_dict())

    lines = scene.get("lines", []) or []
    if only_speaker is not None:
        lines = [ln for ln in lines if ln.get("speaker") == only_speaker]
        measured["only_speaker"] = only_speaker
    max_gap = float(scene.get("max_gap_within_line_s", DEFAULT_MAX_GAP_WITHIN_LINE_S))
    min_turn_gap = float(scene.get("min_gap_between_speakers_s", DEFAULT_MIN_GAP_BETWEEN_SPEAKERS_S))
    clip_s = float(scene.get("clip_duration_s", DEFAULT_CLIP_DURATION_S))

    result = verify.align_lines(lines, words)
    matched, unconsumed = result.matched, result.unconsumed
    measured["lines"] = matched
    measured["unconsumed_words"] = [w["text"] for w in unconsumed]

    # --- every scripted line is present, in order ----------------------------
    #: The public API answers this as one aggregate verdict
    #: (``verify.check_all_lines_present``). The receipt emits a row PER LINE
    #: instead, off the same ``found`` flags, because a dub receipt is read by
    #: someone deciding which line to re-render — "1 of 4 missing" does not tell
    #: them which. Same measurement, two renderings; the test suite asserts the
    #: two cannot disagree.
    for i, line in enumerate(matched):
        record(
            "line_present:{0}:{1}".format(i, line.get("speaker")),
            line.get("found"),
            line.get("text") if line.get("found") else "NOT FOUND: " + str(line.get("text")),
            "the scene script is the contract",
        )

    found = [m for m in matched if m.get("found")]

    # --- nothing the script did not ask for ----------------------------------
    #: Delegated verbatim to the public API. The ByteDance reference-bleed trap
    #: this traces to is not a video defect — an audio reference carrying
    #: dialogue makes the model re-speak lines the prompt omitted, whatever the
    #: prompt was for — so the check belongs to every consumer, not to this CLI.
    record_check(verify.check_no_invented_speech(result))

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
    #:
    #: The mapping comes from ``verify.casting_map`` — one computation, which the
    #: public API's ``check_one_voice_per_line`` also reads. The receipt splits
    #: the verdict into the two rows below because they fail in opposite
    #: directions and are fixed differently: a re-cast character needs the
    #: approved take referenced again, two characters on one voice need a second
    #: node.
    cast = verify.casting_map(result)
    measured["casting"] = cast
    split = [k for k, v in cast.items() if len(v) > 1]
    record(
        "one_voice_per_character",
        not split,
        "clean" if not split else "{0} rendered by more than one voice".format(", ".join(split)),
        "trap: a character re-cast between renders is not a character",
    )

    all_ids = [v[0] for v in cast.values() if len(v) == 1]
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


#: Exit codes. 1 means "the audio failed its contract" — a finding, and the
#: normal way this tool says no. 2 means the tool could not run at all. Keeping
#: them distinct matters in CI: a 1 should fail the build loudly with a receipt
#: to read, a 2 means the invocation itself is wrong.
EXIT_OK = 0
EXIT_CONTRACT_FAILED = 1
EXIT_RUNTIME_ERROR = 2


def _fail(code, message, hint):
    """Emit the structured error shape and return the runtime exit code."""
    payload = {"error": {"code": code, "message": message, "hint": hint}}
    print(json.dumps(payload, indent=2), file=sys.stderr)
    return EXIT_RUNTIME_ERROR


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", help="authored scene JSON")
    parser.add_argument("words", help="diarized word-timestamp JSON from ElevenLabsSpeechToText")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--only-speaker", dest="only_speaker", default=None,
                        help="check a per-character STEM: narrow the contract to this "
                             "character's lines, so any other speech in the stem fails "
                             "no_invented_speech")
    parser.add_argument("--debug", action="store_true",
                        help="re-raise on error instead of printing a structured message")
    args = parser.parse_args(argv)

    try:
        with open(args.scene, "r", encoding="utf-8") as handle:
            scene = json.load(handle)
    except FileNotFoundError:
        if args.debug:
            raise
        return _fail("scene_not_found", "No scene file at {0!r}.".format(args.scene),
                     "Scenes live in docs/scenes/. Pass the path to the .json, not the scene name.")
    except json.JSONDecodeError as exc:
        if args.debug:
            raise
        return _fail("scene_malformed", "{0} is not valid JSON: {1}".format(args.scene, exc),
                     "A scene needs a 'lines' array of {speaker, text} objects.")

    try:
        words = load_words(args.words)
    except FileNotFoundError:
        if args.debug:
            raise
        return _fail("words_not_found", "No transcript at {0!r}.".format(args.words),
                     "Produce one with vo_graphs.transcribe() and save output slot 2 "
                     "(the word list) via SaveText.")
    except json.JSONDecodeError as exc:
        if args.debug:
            raise
        return _fail("words_malformed", "{0} is not valid JSON: {1}".format(args.words, exc),
                     "Expected the word-level transcript, not the plain-text slot 0.")

    # A contract with no lines in it passes every check vacuously, which is the
    # most dangerous possible result: it looks like success. Catch it here — a
    # misspelled --only-speaker is a bad invocation, not a clean stem.
    cast = [ln.get("speaker") for ln in (scene.get("lines") or [])]
    if not cast:
        return _fail("empty_contract", "{0} has no lines.".format(args.scene),
                     "A scene needs a 'lines' array of {speaker, text} objects.")
    if args.only_speaker is not None and args.only_speaker not in cast:
        return _fail(
            "unknown_speaker",
            "No line in {0} is spoken by {1!r}.".format(args.scene, args.only_speaker),
            "Cast in this scene: {0}. Speaker names are case-sensitive.".format(
                ", ".join(sorted({c for c in cast if c}))),
        )

    result = check_dialogue(scene, words, only_speaker=args.only_speaker)

    print(render(result))
    if args.json_path:
        try:
            with open(args.json_path, "w", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2)
        except OSError as exc:
            if args.debug:
                raise
            return _fail("receipt_unwritable",
                         "Could not write the receipt to {0!r}: {1}".format(args.json_path, exc),
                         "Check the directory exists and is writable.")
    return EXIT_OK if all(c["ok"] for c in result["checks"]) else EXIT_CONTRACT_FAILED


if __name__ == "__main__":
    sys.exit(main())
