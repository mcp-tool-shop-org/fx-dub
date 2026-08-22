---
title: Verifying a run
description: Every check in both receipts, and the standard or measured defect each traces to.
sidebar:
  order: 3
---

Run **both** receipts. They answer different questions, and a take can pass one
while failing the other in a way that costs a review cycle.

## The content receipt

```bash
fxdub-dialogue scene.json words.json [--only-speaker NAME] [--json out.json]
```

| Check | Fails when | Traces to |
|---|---|---|
| `line_present:N:SPEAKER` | a scripted line is missing or out of order | the scene script is the contract |
| `no_invented_speech` | the take contains words no line asked for | reference-mode models reproduce their reference's *dialogue*, not just its timbre |
| `no_overlap` | two lines' spans intersect | two characters talking over each other is the worst-sounding failure |
| `no_internal_straggle` | a silence inside one line exceeds its budget | a mid-line pause eats the next character's slot |
| `turn_gaps` | a turn change is tighter than `min_gap_between_speakers_s` | scene pacing |
| `one_voice_per_character` | one character is rendered by more than one voice | a character re-cast between renders is not a character |
| `characters_are_distinct` | two characters share a voice | node-global pitch collapses two speakers into one |
| `fits_clip` | speech runs past `clip_duration_s` | the dub may not outrun the picture |

### Reading a failure

```console
$ fxdub-dialogue scene.json words.json --only-speaker VOICE
9/10 checks pass
| FAIL | no_invented_speech | 4 unscripted word(s): not bad can't complain
```

Four words appear in the VOICE stem that belong to MAC. The stem is contaminated;
mixing it produces two men saying the same line a quarter-second apart.

## The container receipt

```bash
fxdub-receipt <run_dir> [--bed-gain-db N] [--json out.json]
```

| Group | Checks |
|---|---|
| **Deliverables** | mix, both stems, three LUFS manifests, caption, dubbed MP4 all present |
| **Rates** | mix and bed at 48 kHz; VO stem at 48 kHz *or* a known TTS-native rate; delivered rates agree |
| **Loudness** | mix within ±2.0 LU of −18.0; dialogue 8–20 LU above the bed |
| **Video** | the dub carries **both** a video and an audio track; frames intact; duration matches |
| **Caption** | the semantic intermediate reached the manifest and is non-empty |

### The bed meter needs its gain

```bash
fxdub-receipt runs/my-run --bed-gain-db -12
```

EBU R128 integrated loudness gates a quiet bed out of the mix master entirely, so
ducking depth is unmeasurable without a meter on the bed *stem* — and that stem
reads pre-gain. Pass the mix gain you applied, or the separation figure is wrong.

## Gain-stage from the meter, never from memory

The most expensive mixing mistake available here is reusing a working recipe's
numbers after changing engines.

| VO source | Measured on the same line |
|---|---|
| ElevenLabs | −18.34 LUFS |
| ByteDance | **−25.03 LUFS** |

**6.7 dB apart.** Applying the first recipe's gain to the second stem buries the
dialogue — while sample rate, duration and frame count all stay green.

Measure the stem, then compute:

```
VO gain  = target_vo − measured_vo
bed gain = (target_vo − desired_separation) − measured_bed
```

Worked example from the delivered run: VO measured −25.03, target −18.0, so
`+7 dB`. Bed measured −17.20, wanted ~11 LU below the VO, so `−12 dB`. Result:
mix −18.09 LUFS, separation +11.17 LU. Both inside contract, first try.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | every check passed |
| `1` | the audio failed its contract — read the receipt |
| `2` | the tool could not run |

`1` and `2` are deliberately distinct. In CI the first wants its receipt read and
a human to hear the audio; the second means the invocation is wrong and no audio
was ever examined. Collapsing them turns a broken pipeline into a silent green
build.

Errors print the structured shape on stderr:

```json
{
  "error": {
    "code": "words_not_found",
    "message": "No transcript at 'run/words.json'.",
    "hint": "Produce one with vo_graphs.transcribe() and save output slot 2 (the word list) via SaveText."
  }
}
```

Pass `--debug` to re-raise instead of formatting.

## The receipt JSON

`--json out.json` writes the full result: every check with its `ok` flag, detail
string and `traces_to` provenance, plus a `measured` block with the raw numbers.
That file is designed to be archived beside the run — it is the artifact that lets
someone six months later see not just that a take passed, but what it measured.
