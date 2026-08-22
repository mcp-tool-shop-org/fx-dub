<p align="center">
  <a href="README.md">English</a> | <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="docs/assets/logo.png" alt="fx-dub" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/fx-dub/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/fx-dub/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/fx-dub/"><img src="https://img.shields.io/pypi/v/fx-dub.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/fx-dub/"><img src="https://img.shields.io/pypi/pyversions/fx-dub.svg" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/fx-dub/"><img src="https://img.shields.io/badge/landing-page-blue.svg" alt="Landing page"></a>
</p>

**Verify a generated dub before anyone hears it.**

Your text-to-speech model returned 48 kHz stereo at exactly the right duration and
a textbook −18 LUFS. It also said a line you never wrote, in a voice that isn't
your character's, with a two-second hole in the middle.

None of that is visible to sample rate and duration. fx-dub gives you two receipts
— one for the container, one for **what was actually said** — and exits non-zero
when either fails.

```bash
pip install fx-dub
```

```console
$ fxdub-dialogue docs/scenes/night-street.json words.json --only-speaker VOICE
9/10 checks pass
| PASS | line_present:0:VOICE    | Hey, how's it going?
| FAIL | no_invented_speech      | 4 unscripted word(s): not bad can't complain
| PASS | no_overlap              | clean
| PASS | no_internal_straggle    | clean
| PASS | one_voice_per_character | clean
```

That failure is real. A model in `audio reference` mode reproduced its reference
clip's *dialogue*, not just its timbre — so a stem meant to carry one character's
lines quietly re-spoke the other's. Mixed under the real take, it sounded like two
men talking over each other. Sample rate: perfect. Duration: perfect.

## The two receipts

| | Checks | Catches |
|---|---|---|
| **`fxdub-receipt`** | deliverable set, 48 kHz masters, EBU R128 loudness, dialogue-to-bed ducking depth, re-muxed MP4 carries **both** tracks, frames intact | a silent dub, a truncated dub, dialogue buried in the bed, a mix that missed its target |
| **`fxdub-dialogue`** | every scripted line present and in order, no invented speech, no cross-character overlap, no mid-line straggle, one voice per character, fits the clip | a model inventing lines, a character re-cast between renders, a pause that eats the next cue, two characters collapsed into one voice |

**A failing check is a finding, not a bug in the tool.** Report it; never tune the
threshold to make it green. Every check cites the standard or the measured defect
it traces to, so you can argue with it on the evidence.

## The scene script is the contract

Direction lives in the script, not in an agent's head:

```json
{
  "clip_duration_s": 10.062,
  "lines": [
    { "speaker": "VOICE", "text": "Hey, how's it going?" },
    { "speaker": "MAC",   "text": "Not bad. Can't complain.",
      "max_gap_s": 0.15,
      "direction": "There's no pause in between. A gap here runs into VOICE's next cue." },
    { "speaker": "VOICE", "text": "Good to hear, good to hear." }
  ]
}
```

`max_gap_s` on that line is why the verifier rejects a take a global threshold
would wave through. The note beside it is why the number is 0.15 and not something
else.

`--only-speaker MAC` narrows the contract to one character, which is how you check
a **per-character stem**: it should carry that character's lines and *silence*
where anyone else talks. Checking a stem against the whole scene hides exactly the
bug above.

## Getting a transcript

`fxdub-dialogue` reads a word-level diarized transcript — `{text, start, end,
speaker_id}` per word. Any diarizing ASR will do. `fxdub.vo_graphs.transcribe()`
builds the ComfyUI graph for one:

```python
from fxdub import vo_graphs

graph = vo_graphs.transcribe("<storage-key>.flac", "run/words")
# -> API-format dict, ready for your own submit path. Nothing is sent from here.
```

## Graph builders

`fxdub.vo_graphs` also builds the VO-stage graphs: voice design, same-engine audio
reference, clone-and-speak, splice, place-on-timeline, mix. They exist because the
alternative — hand-typing API JSON into a chat window — produces graphs that vanish
with the session and quietly reintroduce defects already paid for once.

Every builder is linted by the repo's trap detectors, so the shapes that cost real
failed jobs cannot be re-authored by accident. Two examples of what that encodes:

- The ElevenLabs clone node's auto-grow input is addressed as `files.audio0` at
  runtime — **not** the `files.item_1` its own schema advertises — and a dry run
  accepts the wrong name without complaint.
- ByteDance's `pitch_rate` is node-global, so one node cannot voice two characters
  at different pitches. Its timestamps address an absolute output timeline, so the
  fix is one pass per character, layered.

Building a graph is a pure function from arguments to a `dict`. **Nothing in this
package submits, uploads, or spends.**

## Threat model

fx-dub runs locally and makes no network calls of any kind.

- **Data touched:** only the files you name on the command line — FLAC/MP4 masters,
  LUFS manifests, caption text, transcript JSON. It writes one receipt, at the
  `--json` path you choose.
- **Data NOT touched:** no credentials, no API keys, no environment secrets, no
  files outside the paths you pass.
- **Permissions required:** filesystem read on the inputs; filesystem write only if
  you pass `--json`.
- **Network egress: none.** There is no HTTP client here and the runtime dependency
  list is empty by design — CI fails the build if that ever changes.
- **Telemetry: none.** Nothing is collected, counted, or transmitted.

Media parsing is standard-library only: FLAC `STREAMINFO` and MP4 atoms are decoded
directly rather than shelling out to `ffprobe`. Malformed input yields a failed
check, not a crash. Full policy in [SECURITY.md](SECURITY.md).

## Exit codes

| Code | Meaning |
|---|---|
| `0` | every check passed |
| `1` | the audio failed its contract — read the receipt |
| `2` | the tool could not run — bad path, malformed JSON, unknown speaker |

`1` and `2` stay distinct on purpose: in CI the first wants its receipt read, the
second means the invocation is wrong. Errors print `{code, message, hint}` on
stderr; `--debug` re-raises instead.

## The pipeline these receipts verify

fx-dub began as a ComfyUI-native dubbing pipeline and still is one. It runs on
[Comfy Cloud](https://cloud.comfy.org):

```
video ─► describe (Florence-2, pinned, single mid-clip frame)
              │ caption.txt
              ▼
        audio prompt (positive claims only — negation collapses in audio-text models)
              ├──────────► ambience bed (ElevenLabs eleven_sfx_v2, 48 kHz, exact duration)
              │                    │ stem_bed.flac
   your script ──────────► dialogue (per-character passes, layered on an absolute timeline)
                                   │ stem_vo.flac
                                   ▼
                    mix bus (48 kHz · dialogue-anchored · −18 LUFS)
                                   │ mix.flac + LUFS manifests
                                   ▼
                        re-mux ─► dubbed.mp4
```

> **"Re-mux"** = re-multiplex: the finished soundtrack is written back into the
> video container, pixels untouched. Not a typo for "remix" — the mixing happens
> one stage earlier; this is the step that hands you a playable `dubbed.mp4`.

**Gain-stage from the meter, never from remembered numbers.** Engines differ by
8 dB on the same line: swapping one TTS for another moved a VO stem from −18.34 to
−25.03 LUFS. Reusing the previous recipe's fixed gain would have buried the
dialogue by 7 dB while every other check stayed green.

## What's honest about this design

- **Captions carry meaning, not timing.** A caption-mediated pipeline is ambience-
  and dialogue-grade; it will never sync a door-slam by prose alone. Impact-grade
  timing needs an event timeline — the
  [Knowledge Base](docs/knowledge-base.md#stage-2b--direct-videoaudio-the-sync-first-alternative)
  maps the direct video→audio models that do it natively, and their licences.
- **A scene description is not a script.** You write the words your characters say;
  the pipeline makes them sound right.
- **Voice identity is not free.** Prompt-designed voices are non-deterministic
  *regardless of seed* — a voice you approve cannot be recalled by re-running the
  same prompt. Cast once, keep the approved audio, then reference or splice it
  forever after. Cross-engine cloning does not preserve identity either. This is
  the most expensive lesson in the repo's trap ledger, and the verifier's
  `one_voice_per_character` check is how it stays learned.
- **Mix numbers come from standards and listening studies** (BS.1770-5,
  AES TD1008, JAES ducking research), not vibes — and they're knobs, because
  preferences measurably differ.
- **Governance is a feature.** Do not clone a real person's voice without consent.
  Synthetic speech published in the EU carries an Article 50
  machine-readable-marking obligation; the receipt JSON is built to be part of that
  provenance trail, and the
  [KB's publishing section](docs/knowledge-base.md#publishing--governance-read-before-you-ship-a-dubbed-video)
  tells you what disclosure you owe where you post. No person-specific voice packs,
  ever. Not for robocalls.

## Status

**v1.0.0 — the pipeline is delivered and both receipts are green.** A two-character
night-street scene scores **19/19** on the container contract (48 kHz, −18.09 LUFS,
dialogue +11.17 LU over the bed, 161 frames intact, 10.069 s) and **11/11** on the
content contract. 167 tests, CI green. Full history in the [CHANGELOG](CHANGELOG.md).

| Piece | State |
|---|---|
| [Handbook](https://mcp-tool-shop-org.github.io/fx-dub/handbook/) — install, usage, scene scripts, graph builders, verification | ✅ |
| [Design rationale](docs/design/2026-08-21-fxdub-v1.dispatch.md) — 45 sourced findings behind every default | ✅ citations externally verified ([record](docs/design/2026-08-21-fxdub-v1.dispatch.verify.md), Ed25519 receipt in-repo) |
| [Knowledge Base](docs/knowledge-base.md) — every option, honest licences, measured costs | ✅ |
| [Agent onboarding](AGENTS.md) + project database ([kb/fxdub.db](kb/README.md)) — nodes, models, runs, **65 measured traps**, decisions | ✅ live; rebuilt each session |
| Spot-effects event timeline · local-GPU lane | ⏳ roadmap |

## For agents and LLMs

Start at [AGENTS.md](AGENTS.md) — the durable operating manual — then
[HANDOFF.md](HANDOFF.md) for live state, then query `kb/fxdub.db` for the trap
ledger. A machine-readable summary is published at
[`/fx-dub/llms.txt`](https://mcp-tool-shop-org.github.io/fx-dub/llms.txt).

## Provenance

This repo practises receipts-first development: graphs are pulled from the platform
and verified (billing feed, decoded output headers) rather than trusted from
reports; design citations pass an external different-family verifier before they
become architecture; measured numbers carry their job UUIDs. When a trap is found,
the same commit adds the detector, the database seed, and the test.

## License

[MIT](LICENSE) — the repo and the package. Model weights carry their own licences;
the [Knowledge Base](docs/knowledge-base.md) is the honest map. © 2026 mcp-tool-shop.

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
