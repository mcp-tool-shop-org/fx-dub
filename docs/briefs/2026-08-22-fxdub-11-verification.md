# fx-dub round 11 — VERIFICATION (our side)

**Date:** 2026-08-22 · **Round:** 11
**Brief:** `2026-08-22-fxdub-11-brief.md` · **Reply:** `2026-08-22-fxdub-11-reply.md`

**Headline: the reply's Item 4 is refuted by execution. Voice cloning works, and
the round-11 brief was overtaken before it was answered** — every question in it
was settled advisor-side by direct probing of the live node catalog plus free
`dry_run` validation, which needs no in-app-agent round trip.

---

## 1. The refutation — cloning works

**Claim:** *"DEFINITIVE: No. You cannot wire LoadAudio into the ElevenLabs clone
node… Recommend dropping the clone route entirely."*

**Refuted, Class A (measured on-account).**

| | |
|---|---|
| Job | `920dc2e0-e420-473a-9cb9-45b84b0fea65` |
| Status | `completed` |
| Graph | `LoadAudio` → `ElevenLabsInstantVoiceClone` → `ElevenLabsTextToSpeech` → `SaveAudioAdvanced` |
| Reference | `08a6480949a5ba27f05fba34eb44651d3a610b8cf71384082b8366413505a00f.flac` (the v2.7 VO stem, a real voice) |
| Output | `5901a7003715bc26b22f4864ebdd25163b802c3e3d23eaa6a05afb8818e76511.flac` — decoded locally: **48 000 Hz, 1 ch, 3.520 s, 169 133 bytes** |

**The API-format shape the brief asked for:**

```json
"2": { "class_type": "ElevenLabsInstantVoiceClone",
       "inputs": { "files.audio0": ["1", 0], "remove_background_noise": false } }
```

**The slot name is `files.audio0`.** Not `files.item_1`, which is what `get_node`
advertises. The platform itself supplied the correct name in the failure of the
first attempt (job `2e0bfd80-5b5c-4ccd-afac-d1b2f3d38862`):

```
"type": "required_input_missing", "details": "audio0",
"extra_info": { "input_name": "files.audio0" }
```

A node that names a missing input is a node that wants one. `COMFY_AUTOGROW_V3`
is a container declaration; the slots it grows carry ordinary AUDIO links.

## 2. Traps earned

| # | Trap | Class |
|---|---|---|
| 1 | **`ElevenLabsInstantVoiceClone.files` runtime slot is `files.audio0`**, not the `files.item_1` `get_node` advertises. Detector: `graph_lint.api_autogrow_slot_name`. | A |
| 2 | **A `dry_run` PASS is not proof of execution.** Pre-flight validates node existence, link integrity and required-input presence against a bundled catalog; it does **not** validate dotted auto-grow / dynamic-combo slot *names*. Two shapes passed `dry_run` then failed at runtime (`files.item_1`, `model.voices.item_1`). **This one is ours** — we reported "all four wiring paths validated" on a `dry_run` basis. | A |
| 3 | **`COMFY_AUTOGROW_V3` is not a wire type.** Querying its producers returns zero and invites a false impossibility claim. Third instance of this trap class in the thread. | A |
| 4 | **`FishAudioTextToSpeech` rejects `model.voices.item_1` at execution** ("unexpected keyword argument") though `get_node` lists it with `auto_grow_slots`. The `s1` model's single `model.voice` input works. | A |
| 5 | **`AudioPad` is broken on Comfy Cloud** — `UnboundLocalError: pad_samples` on every call. Use `EmptyAudio` + `AudioConcat`. | A |
| 6 | **`ByteDanceSeedAudio.pitch_rate` is node-global** — it shifts every speaker in the prompt, so one node cannot voice two characters. Its timestamps address an **absolute output timeline** (a line at `[2.3s:4.0s]` renders 4.032 s with the leading silence written in), so per-character passes layer without alignment work. | A |
| 7 | **ByteDance `audio reference` mode reproduces the reference clip's DIALOGUE CONTENT**, not just its timbre. A four-line reference re-spoke a line the prompt omitted; mixed against the real take it read as two men talking over each other. | A |
| 8 | **Cross-engine cloning does not preserve identity.** A ByteDance voice cloned into ElevenLabs came back approximated and was rejected by ear. | A |
| 9 | **ByteDance text-only voice design is non-deterministic REGARDLESS of seed** (its own spec). A voice approved in one render cannot be recalled. **Cast once → lock the take → perform from it.** | A |
| 10 | **Container metrics cannot see content defects.** Two VO stems passed 48 kHz / correct-duration / clean-LUFS and were rejected by ear within seconds. → `tools/dialogue_receipt.py`. | A |

## 3. Item 3 closed — `eleven_v3` audio tags DO work

The agent declined to claim this untested; we settled it.

Identical voice (`Bill`), seed, stability and speed; the only difference is the
tags:

| Take | Text sent | Duration |
|---|---|---|
| D | `[gruff] Not bad. [tired] Can't complain.` | **2.880 s** |
| E | `Not bad. Can't complain.` | **2.240 s** |

Transcribing D returns **`Not bad. Can't complain`** — the tags are consumed as
delivery directives, **not spoken**. Tags work, and they measurably alter the
performance (+0.64 s, +29 %).

## 4. Corrected engine inventory (`category: partner/audio`, 16 nodes, 5 engines)

| Engine | Nodes | Notes |
|---|---|---|
| **ElevenLabs** | VoiceSelector (21 presets), TextToSpeech, **TextToDialogue** (multi-speaker, up to 10 entries, each with its own voice), **SpeechToSpeech**, InstantVoiceClone, TextToSoundEffects, SpeechToText, AudioIsolation | 48 kHz via `opus_48000_192`. TextToDialogue and SpeechToSpeech had **never been surveyed** before this round. |
| **Fish Audio** | TextToSpeech (s2.1-pro / s1, emotion cues, `@Voice` multi-speaker), VoiceSelector (17 presets + custom voice ID), InstantVoiceClone, SpeechToText | **On the platform**, contrary to the reply. 44.1 kHz mono observed. |
| **ByteDance Seed Audio 1.0** | ByteDanceSeedAudio | 40 presets · 4 reference modes (text / audio / image / preset) · 8 k–48 kHz selectable · `pitch_rate` ±12 semitones · per-line timestamp control |
| **HeyGen** | TextToSpeechNode | 67 voices, SSML, `custom_voice_id`. Measured **44 100 Hz MONO** — reintroduces the rate mismatch ElevenLabs removes. |
| **Sonilo** | TextToMusic, VideoToMusic | music only |

## 5. Process finding

The brief asked the agent five questions. **Four were answerable advisor-side in
minutes** using `get_node`, `search_nodes` and free `dry_run` validation; the
fifth needed one paid job. The round trip added a day and produced a
recommendation that would have deleted the answer.

**Standing consequence:** when a question is answerable from the live catalog or
by a cheap execution, answer it. Reserve briefs for what genuinely needs the
agent's canvas. Our own trap #2 above is the counterweight — probing advisor-side
is only better if the probe is an *execution*, not a `dry_run`.

## 6. Scoreboard

| | Rounds 1–10 | Round 11 |
|---|---|---|
| Our defects | 3 | **1** (dry_run false positive) |
| Agent defects | 0 | **3** |

The agent's four-round record of honest gap declarations stands, and it was right
against us in round 9. **Verify, don't relay — but that is not "assume wrong."**
Round 11 is the round where the check earned its keep in the other direction.

## 7. Outcome

The dub was delivered the same session: `runs/2026-08-22-v28-bytedance/` scores
**19/19** on the container contract and **11/11** on the new content contract, with
both voices approved by ear. fx-dub then shipped as
**[fx-dub 1.0.0 on PyPI](https://pypi.org/project/fx-dub/)**.
