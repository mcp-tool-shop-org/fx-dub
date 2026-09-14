#!/usr/bin/env python3
"""fx-dub's declared public API — align *spoken content* against a script.

This module is the stable surface third-party tools build on. Everything else in
``fxdub`` is either a console script or an internal detail that may move between
releases; what is exported here will not change shape without a major version.

WHY IT EXISTS
-------------
fx-dub was written to catch a failure class that container metrics cannot see:
audio that is the right duration, the right sample rate and the right loudness,
and says **the wrong words**. ``tools/audition_receipt.py`` passed green on two
takes that were rejected by ear within seconds — one carried a fourth line
nobody scripted, the other held a pause long enough to run into the next
character's cue.

That failure class is not specific to video dubs. Any pipeline that turns
authored text into generated speech can drop a line, invent one, or render two
characters in a single voice — and a passing test suite is no evidence against
it, because the defect lives in the audio, not in the code. So the alignment
core is exposed here, medium-agnostic, rather than left as an internal of a
video tool.

WHAT IS *NOT* HERE, DELIBERATELY
--------------------------------
* **No transcription.** fx-dub consumes word timings it is *given*. That is why
  it has zero runtime dependencies and can promise no network egress. Producing
  word timings — ASR, diarization — is the caller's job.
* **No budgets or thresholds.** Every threshold in ``dialogue_receipt`` traces to
  a defect caught by ear in one specific medium, not to a standard. They are
  policy, and they stay with the caller that owns the policy.
* **No medium-specific checks.** Overlap, mid-line straggle, ducking depth, MP4
  frame counts, caption-vs-cast: those live in ``dialogue_receipt`` and
  ``audition_receipt``. A consumer rendering sequential single-track narration
  has no bed to duck under and no concurrent speaker, and a check that cannot
  meaningfully fire is worse than no check — it reads as a pass.

THE THREE CHECKS HERE ARE THE ONES THAT TRANSFER
------------------------------------------------
A line the script asked for must be spoken; a line it did not ask for must not
be; and a character must be rendered by one voice, their own. Those hold for a
dub, an audiobook, a screen reader and a voice assistant alike.

USAGE
-----
::

    from fxdub import verify

    lines = [{"speaker": "narrator", "text": "Chapter one begins here."}]
    words = [{"text": "Chapter", "start": 0.0, "end": 0.4, "speaker": "s0"},
             {"text": "one",     "start": 0.4, "end": 0.7, "speaker": "s0"},
             {"text": "begins",  "start": 0.7, "end": 1.1, "speaker": "s0"},
             {"text": "here",    "start": 1.1, "end": 1.5, "speaker": "s0"}]

    result = verify.align_lines(lines, words)
    for check in (verify.check_all_lines_present(result),
                  verify.check_no_invented_speech(result),
                  verify.check_one_voice_per_line(result)):
        print(check.name, check.ok, check.detail)

Nothing in this module performs IO, and nothing raises on a *finding* — a
missing line is a result, not an exception. See :func:`align_lines`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence, TypedDict

__all__ = [
    "Word",
    "Line",
    "MatchedLine",
    "AlignResult",
    "Check",
    "normalize_text",
    "normalize_words",
    "align_lines",
    "casting_map",
    "check_all_lines_present",
    "check_no_invented_speech",
    "check_one_voice_per_line",
]


#: Words are compared with punctuation and case stripped: a TTS engine's comma
#: placement is not a content defect, and a transcriber's punctuation is its own
#: guess. Apostrophes are KEPT on purpose — "cant" and "can't" are the same word,
#: but dropping the mark makes the diff in a receipt unreadable, and a receipt
#: nobody can read is a receipt nobody checks.
_PUNCT = re.compile(r"[^a-z0-9']+")


# --------------------------------------------------------------------------
# Types
# --------------------------------------------------------------------------

class _WordRequired(TypedDict):
    text: str
    start: float
    end: float


class Word(_WordRequired, total=False):
    """One timed token of rendered speech.

    ``text`` is the spoken word, ``start``/``end`` its seconds from the start of
    the audio, ``speaker`` whatever id the diarizer assigned (``None`` when the
    transcript is not diarized). ``tokens`` is set by :func:`normalize_words` and
    is an internal detail — build words without it.
    """

    speaker: str | None
    tokens: list[str]


class _LineRequired(TypedDict):
    speaker: str
    text: str


class Line(_LineRequired, total=False):
    """One scripted line: who says it and what they say.

    ``max_gap_s`` is an optional per-line pause budget. This module does not read
    it — it is carried through to :attr:`AlignResult.matched` so a caller that
    owns a pause policy (``fxdub.dialogue_receipt`` does) can apply it.
    """

    max_gap_s: float | None


class _MatchedRequired(TypedDict):
    speaker: str | None
    text: str | None
    found: bool


class MatchedLine(_MatchedRequired, total=False):
    """A scripted line and where it was found in the rendered audio.

    Only ``speaker``, ``text`` and ``found`` are always present: when ``found``
    is ``False`` there is nothing measured to report. When it is ``True`` the
    entry also carries ``start``/``end`` (seconds), ``diarized_speaker`` (see
    :func:`align_lines` — it is a **majority vote**, not an assertion),
    ``max_internal_gap_s`` (the widest silence between two consecutive tokens
    inside the line) and ``max_gap_s`` copied from the :class:`Line`.

    These are plain dicts rather than objects so a receipt can be
    ``json.dump``-ed without a conversion step.
    """

    start: float
    end: float
    diarized_speaker: str | None
    max_internal_gap_s: float
    max_gap_s: float | None


@dataclass(frozen=True)
class AlignResult:
    """What :func:`align_lines` measured. Findings, not exceptions.

    :attr:`matched` has one entry per scripted line, in script order, whether or
    not it was found. :attr:`unconsumed` is every rendered token that no scripted
    line claimed.
    """

    matched: list[MatchedLine]
    unconsumed: list[Word]

    @property
    def missing(self) -> list[MatchedLine]:
        """Scripted lines that were not spoken, in script order."""
        return [m for m in self.matched if not m.get("found")]

    @property
    def invented_words(self) -> list[Word]:
        """Rendered tokens no scripted line claimed — speech nobody asked for.

        The same list as :attr:`unconsumed`, under the name that says what it
        *means*: ``unconsumed`` describes the mechanism, ``invented_words``
        describes the defect. This is the detector that would have caught the
        phantom fourth line before it reached a mix.
        """
        return self.unconsumed


@dataclass(frozen=True)
class Check:
    """One verdict, and the reason it is worth checking.

    ``traces_to`` is not decoration. Every check in fx-dub cites the standard or
    the measured defect it exists for, so that a failing receipt can be read by
    someone who was not there — and so that a check nobody can justify gets
    deleted instead of tuned until it is green.
    """

    name: str
    ok: bool
    detail: str
    traces_to: str

    def as_dict(self) -> dict:
        """The receipt row shape fx-dub's own receipts use (``check``, not ``name``)."""
        return {
            "check": self.name,
            "ok": self.ok,
            "detail": self.detail,
            "traces_to": self.traces_to,
        }


# --------------------------------------------------------------------------
# Normalization
# --------------------------------------------------------------------------

def normalize_text(text: str) -> list[str]:
    """Split text into comparable word tokens.

    Lowercases, drops punctuation, keeps apostrophes, collapses whitespace::

        >>> normalize_text("Not bad. Can't complain!")
        ['not', 'bad', "can't", 'complain']

    ``None`` and ``""`` both yield ``[]``. This is the *only* text comparison in
    the API: two words are the same word when their normalized forms are equal.
    """
    return [w for w in _PUNCT.sub(" ", (text or "").lower()).split() if w]


def normalize_words(raw: Any) -> list[Word]:
    """Coerce a transcript into the internal word shape.

    **Accepted input** — pass whatever your transcriber emitted:

    * a **bare list** of word entries;
    * an **object with a** ``"words"`` **key** holding that list (the shape
      ``ElevenLabsSpeechToText`` emits with ``model.diarize=true`` and
      ``model.timestamps_granularity="word"``);
    * the **output of this function**, unchanged — it is idempotent, so a caller
      may normalize defensively without checking whether it already happened.

    **Per entry**, all fields optional unless noted:

    ==================  ====================================================
    ``text``            required in practice; an entry whose text normalizes
                        to nothing is dropped
    ``start`` / ``end`` seconds, coerced with ``float()``, default ``0.0``
    ``speaker_id``      preferred speaker id
    ``speaker``         fallback speaker id when ``speaker_id`` is absent
    ``type``            must be absent or ``"word"``
    ==================  ====================================================

    **Dropped**, deliberately: non-dict entries; entries whose ``type`` is
    anything other than ``"word"`` (ElevenLabs emits ``"spacing"`` and
    ``"audio_event"``, which carry no text to match and whose timings would
    corrupt a gap measurement); and entries that normalize to no tokens.

    An entry whose text holds several words — a transcriber that fuses ``"New
    York"`` into one entry — keeps its span and is split across its tokens at
    match time, so the fusion does not break alignment.

    :raises TypeError: if ``raw`` is neither a list nor an object with
        ``.get`` — a clear failure beats an ``AttributeError`` from three frames
        down.
    """
    if isinstance(raw, list):
        words = raw
    elif hasattr(raw, "get"):
        words = raw.get("words", [])
    else:
        raise TypeError(
            "normalize_words() takes a list of word entries, or an object with a "
            "'words' key; got {0}.".format(type(raw).__name__)
        )

    out: list[Word] = []
    for entry in words:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") not in (None, "word"):
            continue
        tokens = normalize_text(entry.get("text", ""))
        if not tokens:
            continue
        out.append({
            "text": tokens[0] if len(tokens) == 1 else " ".join(tokens),
            "tokens": tokens,
            "start": float(entry.get("start", 0.0)),
            "end": float(entry.get("end", 0.0)),
            "speaker": entry.get("speaker_id") or entry.get("speaker"),
        })
    return out


def _flatten(words: Sequence[Word]) -> list[Word]:
    """One entry per token, so a transcriber that fuses two words still aligns.

    A fused entry's span is divided evenly across its tokens. Those per-token
    times are an interpolation, not a measurement — which is fine for the
    ordering and gap questions this module answers, and is why nothing here
    reports a token time as an extent.
    """
    flat: list[Word] = []
    for word in words:
        tokens = word["tokens"]
        span = (word["end"] - word["start"]) / max(len(tokens), 1)
        for i, token in enumerate(tokens):
            flat.append({
                "text": token,
                "start": word["start"] + i * span,
                "end": word["start"] + (i + 1) * span,
                "speaker": word.get("speaker"),
            })
    return flat


# --------------------------------------------------------------------------
# Alignment
# --------------------------------------------------------------------------

def align_lines(lines: Sequence[Line], words: Any) -> AlignResult:
    """Match each scripted line to a consecutive run of rendered tokens.

    Lines are matched **in order**: each search starts where the previous line's
    match ended, so a line that appears only *before* its scripted position is
    correctly reported missing rather than matched out of sequence.

    ``words`` is passed through :func:`normalize_words`, so raw transcriber JSON,
    a bare list of :class:`Word` dicts, or already-normalized output all work.

    **A line that cannot be found is returned with** ``found=False`` **rather
    than raising.** A missing line is a finding, and the receipt should still
    report everything else — a verifier that stops at the first defect makes the
    second defect cost another render.

    ``diarized_speaker`` on a matched line is a **majority vote** over the
    speaker ids of that line's tokens. It is evidence about who rendered the
    line, not an assertion: a diarizer that splits one voice across two ids, or
    merges two voices into one, is a known failure mode of diarization itself.
    Treat a casting finding as a reason to listen, not as proof.

    Returns an :class:`AlignResult`. Never performs IO.
    """
    flat = _flatten(normalize_words(words))
    cursor = 0
    matched: list[MatchedLine] = []
    claimed: set[int] = set()

    for line in lines:
        want = normalize_text(line.get("text", ""))
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
        speakers = [w["speaker"] for w in run if w.get("speaker") is not None]
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
    return AlignResult(matched=matched, unconsumed=unconsumed)


def casting_map(result: AlignResult) -> dict[str, list[str]]:
    """Scripted speaker → the diarized voice ids that rendered their lines.

    Insertion-ordered by first appearance in the script; each value sorted. Lines
    that were not found, and lines whose tokens carried no speaker id, contribute
    nothing — an undiarized transcript yields ``{}`` and every casting question
    is then unanswerable rather than falsely clean.

    A healthy render is a **bijection**: one id per speaker, and no id shared. A
    speaker with two ids was re-cast mid-render; two speakers with one id were
    collapsed into a single voice. :func:`check_one_voice_per_line` reports both.
    """
    cast: dict[str, set] = {}
    for line in result.matched:
        if not line.get("found"):
            continue
        voice = line.get("diarized_speaker")
        if voice is not None:
            cast.setdefault(line["speaker"], set()).add(voice)
    return {speaker: sorted(voices) for speaker, voices in cast.items()}


# --------------------------------------------------------------------------
# Checks — medium-agnostic only
# --------------------------------------------------------------------------

def check_all_lines_present(result: AlignResult) -> Check:
    """Every scripted line was spoken, in script order.

    Catches the whole family of *silent truncation* defects: a chapter dropped by
    a partial render and reported as success, a line lost to a retry, a segment
    that failed to synthesize and left no trace in the container. Duration does
    not catch these — a 29-of-30-chapter audiobook is a perfectly valid file.
    """
    missing = result.missing
    total = len(result.matched)
    if not missing:
        return Check(
            name="all_lines_present",
            ok=True,
            detail="all {0} scripted line(s) present, in order".format(total),
            traces_to="the script is the contract",
        )
    shown = "; ".join(
        "[{0}] {1!r}".format(m.get("speaker"), (m.get("text") or "")[:48])
        for m in missing[:6]
    )
    return Check(
        name="all_lines_present",
        ok=False,
        detail="{0} of {1} line(s) missing: {2}".format(len(missing), total, shown),
        traces_to="the script is the contract",
    )


def check_no_invented_speech(result: AlignResult) -> Check:
    """Nothing was spoken that the script did not ask for.

    Catches speech a generator produced on its own and speech that leaked in from
    the input: a voice engine reproducing a reference clip's *dialogue content*
    along with its timbre; a sentinel or markup token that reached the engine as
    prose and got narrated aloud.

    This is also what makes a **per-character stem** checkable. A stem carries one
    character's lines and silence elsewhere, so a caller aligns it against that
    character's lines alone; every other word the stem contains then shows up
    here as unscripted.
    """
    extra = result.invented_words
    return Check(
        name="no_invented_speech",
        ok=not extra,
        detail="clean" if not extra else "{0} unscripted word(s): {1}".format(
            len(extra), " ".join(w["text"] for w in extra[:12])),
        traces_to="trap: ByteDance audio-reference reproduces the reference's dialogue content",
    )


def check_one_voice_per_line(result: AlignResult) -> Check:
    """Each character is rendered by one voice, and no two share one.

    Both halves matter and they fail in opposite directions:

    * a speaker mapping to **more than one** voice id was re-cast mid-render —
      a character whose voice changes between lines is not a character;
    * **two or more** speakers mapping to the same id were collapsed into one
      voice — the defect that turns a three-hander into a monologue, and the one
      an attribution bug produces most often.

    Reads :func:`casting_map`, so the caveat there applies: ``diarized_speaker``
    is a vote by a model. A finding here means *listen to it*, not *it is proven
    broken*. Silent when the transcript carries no speaker ids at all — with no
    evidence either way, this check makes no claim.
    """
    traces_to = ("traps: a character re-cast between renders is not a character; "
                 "one voice speaking two characters is not two characters")
    cast = casting_map(result)

    if not cast:
        return Check(
            name="one_voice_per_line",
            ok=True,
            detail="no speaker ids in the transcript — casting not evidenced",
            traces_to=traces_to,
        )

    by_voice: dict[str, list[str]] = {}
    for speaker, voices in cast.items():
        if len(voices) == 1:
            by_voice.setdefault(voices[0], []).append(speaker)

    problems = []
    for speaker, voices in cast.items():
        if len(voices) > 1:
            problems.append("{0} rendered by {1} voices ({2})".format(
                speaker, len(voices), ", ".join(voices)))
    for voice, who in by_voice.items():
        if len(who) > 1:
            problems.append("{0} all rendered by one voice ({1})".format(
                ", ".join(who), voice))

    distinct = len({v for voices in cast.values() for v in voices})
    return Check(
        name="one_voice_per_line",
        ok=not problems,
        detail=("{0} character(s) -> {1} distinct voice(s)".format(len(cast), distinct)
                if not problems else "; ".join(problems)),
        traces_to=traces_to,
    )
