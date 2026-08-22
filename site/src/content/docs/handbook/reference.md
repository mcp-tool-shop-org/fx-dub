---
title: Reference
description: CLI flags, exit codes, check names, and the Python API.
sidebar:
  order: 5
---

## fxdub-dialogue

```
fxdub-dialogue <scene.json> <words.json> [--only-speaker NAME] [--json OUT] [--debug]
```

| Argument | Meaning |
|---|---|
| `scene` | Authored scene JSON. See [Scene scripts](../scene-scripts/). |
| `words` | Word-level diarized transcript JSON. |
| `--only-speaker NAME` | Narrow the contract to one character — the mode for per-character stems. Case-sensitive. |
| `--json OUT` | Write the full receipt. |
| `--debug` | Re-raise on error instead of printing the structured shape. |

### Checks

`line_present:N:SPEAKER` · `no_invented_speech` · `no_overlap` ·
`no_internal_straggle` · `turn_gaps` · `one_voice_per_character` ·
`characters_are_distinct` · `fits_clip`

### Error codes

| `code` | Cause |
|---|---|
| `scene_not_found` | no file at the scene path |
| `scene_malformed` | scene is not valid JSON |
| `empty_contract` | the scene has no `lines` |
| `unknown_speaker` | `--only-speaker` names a character absent from the scene |
| `words_not_found` | no file at the transcript path |
| `words_malformed` | transcript is not valid JSON |
| `receipt_unwritable` | `--json` path is not writable |

## fxdub-receipt

```
fxdub-receipt <run_dir> [--bed-gain-db N] [--json OUT] [--debug]
```

| Argument | Meaning |
|---|---|
| `run_dir` | Directory holding the downloaded artifacts. |
| `--bed-gain-db N` | Mix gain applied to the bed, in dB. Required for a correct ducking figure. Default `-9.0`. |
| `--json OUT` | Write the full receipt. |

### Expected files

Matched by `filename_prefix` stem, whatever counter suffix the platform appends:

```
mix*.flac   stem_bed*.flac   stem_vo*.flac
mix_lufs*.txt   vo_lufs*.txt   bed_lufs*.txt
caption*.txt   dubbed*.mp4
```

The `bed_lufs` manifest is **required** — R128 gates a quiet bed out of the mix
master, so ducking depth is unmeasurable without a meter on the bed stem.

### Contract values

| Constant | Value |
|---|---|
| Runtime sample rate | 48 000 Hz |
| Target loudness | −18.0 LUFS, ±2.0 |
| Dialogue over bed | 8–20 LU |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | every check passed |
| `1` | contract failure — a finding, with a receipt to read |
| `2` | runtime error — the tool could not run |

`3` (partial success) is unused: a receipt is all-or-nothing, and there is no
partial verification.

## Python API

```python
from fxdub import audition_receipt, dialogue_receipt, media_probe, vo_graphs
```

### `dialogue_receipt`

| Function | Returns |
|---|---|
| `check_dialogue(scene, words, only_speaker=None)` | `{"checks": [...], "measured": {...}}` |
| `align(scene_lines, words)` | `(matched, unconsumed)` — per-line spans, and every token no line claimed |
| `normalize_words(raw)` | coerce raw node output into the internal word shape |
| `load_words(path)` | the same, from disk |
| `normalize(text)` | comparable word tokens |
| `render(result)` | the markdown table |

`check_dialogue` accepts raw transcript JSON directly — no conversion step needed.

### `audition_receipt`

| Function | Returns |
|---|---|
| `check_run(run_dir, bed_gain_db=-9.0)` | `{"checks": [...], "measured": {...}}` |
| `render(result)` | the markdown receipt |

Never raises on a bad artifact — a malformed file is a failed check, not a crash.

### `media_probe`

| Function | Returns |
|---|---|
| `parse_streaminfo(data)` | FLAC sample rate, channels, bit depth, total samples |
| `probe_mp4(data)` | track handlers, frame count, duration, header validity |
| `parse_lufs(text)` | the float out of a loudness manifest |

Standard library only — no `ffprobe` subprocess.

### `vo_graphs`

See [Graph builders](../graph-builders/). Every function returns an API-format
`dict`; none of them submit.

## Supported platforms

Python 3.10+ on any OS. CI runs 3.10 and 3.12 on Linux. There is no compiled
extension, no subprocess, and no network call, so platform differences are limited
to path handling.

## Security

No network egress, no telemetry, no credential access, zero runtime dependencies —
and CI fails the build if that dependency list ever becomes non-empty. Full threat
model in [SECURITY.md](https://github.com/mcp-tool-shop-org/fx-dub/blob/main/SECURITY.md).
