---
title: The Public API
description: fxdub.verify — the declared, medium-agnostic surface for checking that generated speech says what the script asked for.
sidebar:
  order: 4
---

**`fxdub.verify` is the one module other tools should import.** Everything else in
`fxdub` is a console script or an internal that may move between releases.

The two CLIs verify a *video dub*. The core underneath them — match a script
against what was actually spoken — is not specific to video, so it is exported
separately, documented, and held stable.

```python
from fxdub import verify
```

New in v1.2.0.

## The thirty-second version

```python
lines = [{"speaker": "narrator", "text": "Chapter two continues the tale."}]
words = [                     # from your own ASR — fx-dub does not transcribe
    {"text": "Chapter", "start": 0.0, "end": 0.4, "speaker": "s0"},
    {"text": "two",     "start": 0.4, "end": 0.7, "speaker": "s0"},
    # ...
]

result = verify.align_lines(lines, words)

result.missing            # scripted lines that were never spoken
result.invented_words     # rendered tokens no scripted line claimed

for check in (verify.check_all_lines_present(result),
              verify.check_no_invented_speech(result),
              verify.check_one_voice_per_line(result)):
    print(check.name, check.ok, check.detail)
```

Exit non-zero on any `check.ok is False` and you have a render gate.

## The three checks, and why only three

A line the script asked for must be spoken. A line it did not ask for must not be.
A character must be rendered by one voice, their own.

Those hold for a dub, an audiobook, a screen reader, and a voice assistant alike.
Nothing else in fx-dub does — which is the whole reason the module exists.

### `check_all_lines_present`

Catches silent truncation: a chapter dropped by a partial render and reported as
success, a line lost to a retry, a segment that failed to synthesize and left no
trace. **Duration cannot catch these.** A 29-of-30-chapter audiobook is a perfectly
valid audio file.

### `check_no_invented_speech`

Catches speech the generator produced on its own, and speech that leaked in from
the input — a voice engine reproducing a reference clip's *dialogue content* along
with its timbre, or a sentinel or markup token that reached the engine as prose and
got narrated aloud.

It is also what makes a **per-character stem** checkable. A stem carries one
character's lines and silence elsewhere, so align it against that character's lines
alone; every other word in the stem then shows up as unscripted.

### `check_one_voice_per_line`

Checks the casting **bijection**, in both directions:

- one speaker mapping to **more than one** voice id was re-cast mid-render — a
  character whose voice changes between lines is not a character;
- **two or more** speakers mapping to the same id were collapsed into one voice,
  which is what an attribution bug produces most often.

Use [`casting_map()`](#casting_map) if you want the mapping rather than the verdict.

:::caution[A casting finding means listen, not proven-broken]
`diarized_speaker` is a **majority vote** over a line's tokens, decided by a
diarization model with its own error distribution. Splitting one voice across two
ids, or merging two voices into one, are known failure modes *of diarization
itself*. Treat a finding here as a reason to listen to the take.
:::

If the transcript carries no speaker ids at all, this check returns `ok=True` with
`detail` saying *casting not evidenced* — it makes no claim rather than a false
clean.

## What is deliberately not here

**No transcription.** fx-dub consumes word timings it is given. That is what keeps
`dependencies = []` and the no-network-egress promise honest. Producing timings —
ASR, diarization — is yours.

**No thresholds.** Every budget in `dialogue_receipt` traces to a defect caught by
ear in one specific medium, not to a standard. They belong to the caller that owns
the policy.

**No medium-specific checks.** Overlap, mid-line straggle, clip fit, ducking depth,
caption-vs-cast all stay in the CLIs. A consumer rendering sequential single-track
narration has no bed to duck under and no concurrent speaker, and **a check that
cannot meaningfully fire is worse than no check, because it reads as a pass.**

## Reference

### `normalize_text(text) -> list[str]`

Lowercases, drops punctuation, keeps apostrophes, collapses whitespace.

```python
verify.normalize_text("Not bad. Can't complain!")
# ['not', 'bad', "can't", 'complain']
```

Apostrophes are kept on purpose: *cant* and *can't* are the same word, but dropping
the mark makes the diff in a receipt unreadable, and a receipt nobody can read is a
receipt nobody checks.

### `normalize_words(raw) -> list[Word]`

Pass whatever your transcriber emitted — a bare list, an object with a `"words"`
key (the shape `ElevenLabsSpeechToText` produces with `diarize=true` and
`timestamps_granularity="word"`), or the output of this function again. It is
**idempotent**, so you may normalize defensively without checking.

Per entry: `text` (required in practice), `start`/`end` in seconds, `speaker_id`
preferred over `speaker`, and `type` absent or `"word"`. Entries typed `spacing` or
`audio_event` are dropped — they carry no text to match and their timings would
corrupt a gap measurement. An entry fusing several words keeps its span and is split
across its tokens at match time.

Raises `TypeError` on anything that is neither a list nor a mapping.

### `align_lines(lines, words) -> AlignResult`

Matches each scripted line to a consecutive run of rendered tokens, **in script
order** — each search starts where the previous match ended, so a line that appears
only *before* its scripted position is correctly reported missing rather than matched
out of sequence.

A line that cannot be found comes back with `found=False` **rather than raising**. A
missing line is a finding, and the receipt should still report everything else — a
verifier that stops at the first defect makes the second defect cost another render.

Performs no IO.

### `AlignResult`

| | |
|---|---|
| `matched` | one entry per scripted line, in script order, found or not |
| `unconsumed` | every rendered token no scripted line claimed |
| `.missing` | the `matched` entries with `found=False` |
| `.invented_words` | the same list as `unconsumed`, under the name that says what it *means* |

Entries are plain dicts so a receipt can be `json.dump`-ed without a conversion step.
A found entry also carries `start`, `end`, `diarized_speaker`, `max_internal_gap_s`,
and the `max_gap_s` copied from the line.

### `casting_map(result) -> dict[str, list[str]]`

Scripted speaker → the diarized voice ids that rendered their lines. An undiarized
transcript yields `{}`, so every casting question is unanswerable rather than falsely
clean.

### `Check`

`name`, `ok`, `detail`, `traces_to`. Call `.as_dict()` for the receipt row shape
fx-dub's own receipts use (the key is `check`, not `name`).

`traces_to` is not decoration — every check cites the standard or the measured defect
it exists for, so a failing receipt can be read by someone who was not there, and so
a check nobody can justify gets deleted instead of tuned until it is green.

## The CLI is a consumer of this API

`fxdub-dialogue` computes its content verdicts *through* `verify` and adds only what
makes a receipt a dub receipt. That is enforced by tests that sabotage `verify` and
require the CLI to break with it.

It matters because the alternative has a name. The tool that drove this API out of
`fx-dub` had a compliance checker that no render path ever called — correct code,
verifying nothing, for two major versions. **A public surface the shipping tool does
not itself exercise is that shape waiting to happen.**

## Proven against a second codebase

Before being declared, the API was run against four content defects measured in an
EPUB→audiobook renderer with no video, no music bed and no concurrent speakers — a
narrated footnote sentinel, a chapter dropped by a partial render and reported as
`success`, three characters collapsed into one voice, and markup read aloud as prose.
Its 1235 passing tests saw none of them.

All four are fixtures in `tests/test_verify.py`, **beside a clean control that must
report nothing.** A check that only ever fires is as broken as one that never does.
