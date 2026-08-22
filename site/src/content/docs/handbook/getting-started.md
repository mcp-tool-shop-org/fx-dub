---
title: Getting Started
description: Install fx-dub and read your first receipt.
sidebar:
  order: 1
---

## Install

```bash
pip install fx-dub
```

Requires Python 3.10 or newer. **Zero runtime dependencies** — the package is pure
standard library, so there is nothing to resolve and nothing that can break it
from underneath.

Two console scripts are installed:

```bash
fxdub-receipt --help    # the container receipt
fxdub-dialogue --help   # the content receipt
```

## Your first content check

`fxdub-dialogue` needs two files: the scene your take was supposed to perform, and
a word-level diarized transcript of what it actually performed.

**1. Write the scene.** This is the contract:

```json title="scene.json"
{
  "clip_duration_s": 10.062,
  "lines": [
    { "speaker": "VOICE", "text": "Hey, how's it going?" },
    { "speaker": "MAC",   "text": "Not bad. Can't complain." },
    { "speaker": "VOICE", "text": "Good to hear, good to hear." }
  ]
}
```

**2. Transcribe the take.** Any diarizing ASR works. fx-dub expects a JSON list of
words, each with `text`, `start`, `end`, and `speaker_id`:

```json title="words.json"
[
  { "text": "Hey",  "start": 0.60, "end": 0.78, "speaker_id": "speaker_0", "type": "word" },
  { "text": "how's", "start": 0.80, "end": 1.02, "speaker_id": "speaker_0", "type": "word" }
]
```

If you are on ComfyUI, [`vo_graphs.transcribe()`](./graph-builders/#transcribe)
builds the graph that produces exactly this.

**3. Check it:**

```bash
fxdub-dialogue scene.json words.json
```

```console
11/11 checks pass
| PASS | line_present:0:VOICE      | Hey, how's it going?
| PASS | line_present:1:MAC        | Not bad. Can't complain.
| PASS | no_invented_speech        | clean
| PASS | no_overlap                | clean
| PASS | no_internal_straggle      | clean
| PASS | one_voice_per_character   | clean
| PASS | characters_are_distinct   | 2 character(s) -> 2 distinct voice(s)
| PASS | fits_clip                 | speech ends 9.779s, clip is 10.062s
```

## Checking a single character's stem

If you render characters as separate stems — which you often must, because many
engines apply pitch and delivery knobs per *node*, not per speaker — check each
stem against only its own lines:

```bash
fxdub-dialogue scene.json voice-words.json --only-speaker VOICE
```

A VOICE stem should carry VOICE's lines and **silence** where MAC talks. Anything
else in it is a defect, and `no_invented_speech` will say so.

:::caution[This is the mode that catches reference bleed]
Checking a stem against the *whole* scene hides the bug entirely — MAC's line is
in the script, so a stem that wrongly contains it looks correct. `--only-speaker`
is not a convenience; it is the check.
:::

## Your first container check

Download a run's artifacts into one directory, then:

```bash
fxdub-receipt runs/my-run --bed-gain-db -12 --json receipt.json
```

The tool matches files by `filename_prefix` stem, whatever counter suffix your
platform appends — `mix*.flac`, `stem_bed*.flac`, `stem_vo*.flac`,
`*_lufs*.txt`, `caption*.txt`, `dubbed*.mp4`.

`--bed-gain-db` matters: the bed meter reads the stem *pre-gain*, so recovering
the delivered ducking depth needs the mix gain you applied.

## Wiring it into CI

Both tools exit non-zero on failure, and the two failure modes are distinct:

```bash
fxdub-dialogue scene.json words.json
case $? in
  0) echo "ship it" ;;
  1) echo "the take failed its contract — read the receipt" ; exit 1 ;;
  2) echo "bad invocation — check paths and speaker names" ; exit 2 ;;
esac
```
