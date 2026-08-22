---
title: Graph builders
description: Build ComfyUI VO-stage graphs as code, with the traps already encoded.
sidebar:
  order: 4
---

`fxdub.vo_graphs` builds the ComfyUI graphs for the voice-over stage. Each builder
is a pure function returning an API-format `dict`.

:::note[Nothing here submits anything]
There is no client, no endpoint, and no token in this module. Building a graph
cannot spend credits, upload a file, or make a network call. Submitting one is
entirely your action through your own authenticated tooling.
:::

## Why builders instead of hand-written JSON

Hand-typing API JSON into a chat window produces graphs that vanish with the
session — and reintroduce defects that were already paid for once. In this
project's own history, fifteen graphs were authored that way in a single sitting;
none survived, and several repeated a mistake the trap ledger already recorded.

Every builder here is linted by the repo's API-format detectors, so a shape that
cost a real failed job cannot be re-authored by accident.

## The builders

```python
from fxdub import vo_graphs
```

| Function | Produces |
|---|---|
| `bytedance_text_only(prompt, prefix, pitch_rate, seed, ...)` | voice **design** from a written brief — casting only |
| `bytedance_audio_reference(reference_key, prompt, prefix, ...)` | same-engine voice reference — holds identity |
| `elevenlabs_clone_tts(reference_key, text, prefix, ...)` | clone a voice from a cloud asset, then speak |
| `splice(storage_key, keep_spans, prefix)` | keep only the named spans, butt-joined |
| `place(storage_key, at_seconds, prefix)` | put a clip on a timeline behind generated silence |
| `mix(key_a, key_b, prefix, gain_a_db, gain_b_db)` | overlay two tracks |
| `transcribe(storage_key, prefix)` | word-level diarized transcript — the input to `fxdub-dialogue` |

Cloud audio is addressed by **storage key**: any saved output can be reloaded by
its content hash, which is what makes re-mixing free and deterministic.

## transcribe

The one you need to use `fxdub-dialogue` at all:

```python
graph = vo_graphs.transcribe("<storage-key>.flac", "run/words")
```

Two constraints are baked in because the node rejects the alternatives:

- `num_speakers` must be `0` when diarizing — the node refuses both together
- `diarization_threshold` caps at `0.4` (default `0.22`)

Save **output slot 2** — the word list. Slot 0 is plain text and will not work.

## The voice-identity rule

This is the most expensive lesson in the project, and it shapes which builder you
should reach for.

> **CAST once → LOCK the approved take → PERFORM every later line from it.**

Prompt-designed voice generation is non-deterministic *regardless of seed*. A
voice approved in one render **cannot be recalled** by re-running the same prompt
— you get a different person. So:

| Stage | Builder | Note |
|---|---|---|
| **Cast** | `bytedance_text_only` | Generate until a voice is approved. Then stop. |
| **Lock** | keep the approved audio | The take *is* the character now. |
| **Perform** | `bytedance_audio_reference` or `splice` | Reference it, or cut the existing audio. Never re-render. |

Cross-engine cloning does **not** preserve identity either — a voice cloned from
one engine into another comes back approximated.

## Traps the builders encode

### The clone node's slot name

`ElevenLabsInstantVoiceClone` advertises its auto-grow file input as
`files.item_1`. The runtime wants **`files.audio0`**. A dry run accepts the wrong
name without complaint; only a real execution fails, and the error is the first
place the correct name appears.

```python
CLONE_SLOT = "files.audio0"   # not what get_node says
```

### Node-global pitch

`pitch_rate` on ByteDance Seed Audio is a **node-level** knob — it shifts every
speaker in the prompt by the same interval. One node therefore cannot voice two
characters at different pitches; asking it to collapses them toward one voice.

The fix works because the timestamps address an **absolute output timeline**: a
line written `[2.3s:4.0s]` renders with the leading silence already in it. So
render one pass per character and layer them:

```python
voice = vo_graphs.bytedance_text_only(voice_prompt, "scene/voice", pitch_rate=-3)
mac   = vo_graphs.bytedance_text_only(mac_prompt,   "scene/mac",   pitch_rate=0)
# each pass is full-length with silence where the other talks -> mix them
```

### Reference content bleed

`bytedance_audio_reference` reproduces the reference clip's **dialogue content**,
not just its timbre. Give it a four-line scene as a voice reference and it will
re-speak all four lines regardless of your prompt.

Use a single-speaker reference, and gate every audio-reference render:

```bash
fxdub-dialogue scene.json words.json --only-speaker VOICE
```

The repo's lint marks every audio-reference graph as requiring exactly that check.

### A broken node

`AudioPad` raises `UnboundLocalError: pad_samples` on every call. `place()` uses
`EmptyAudio` + `AudioConcat` instead.

## Repairing an approved take

When a take's voice is right but its timing is not, splice rather than re-render —
the voice stays bit-identical because nothing passes through a model:

```python
words = load_words("take-words.json")
spans = vo_graphs.gap_closing_spans(words, after_index=1, tail=0.05, head=0.035)
graph = vo_graphs.splice("<storage-key>.flac", spans, "take/fixed")
```

`gap_closing_spans` computes the keep-spans that excise the silence after a given
word. In the delivered scene this turned a 1.880 s mid-line hole into 0.13 s
without touching the performance.

## Isolate unproven nodes

A ComfyUI job that fails at any node loses **every** output — completed nodes are
not persisted. When a graph mixes a paid generation with an untested local node,
split them into separate jobs. That rule is why a broken `AudioPad` cost nothing
the day it was discovered.
