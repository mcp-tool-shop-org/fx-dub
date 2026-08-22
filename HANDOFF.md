# fx-dub — session handoff

**PASTE TARGET:** a fresh Claude Code session working in `E:\AI\fx-dub`. You are both advisor and executor. The Director is **Mike**; his live word overrides everything here. Never wrap a session the Director didn't end.

**Written 2026-08-22 at the end of session 3 (supersedes all earlier text).** Read [`AGENTS.md`](AGENTS.md) first (it is the durable operating manual), then this file (which is the *live state*), then query `kb/fxdub.db`. **Verify from receipts and pulled artifacts, never from reports** — that rule has caught a refuted claim, a silent CFG defect, and a clobbered file in this project alone.

---

## 1. What fx-dub is

Video → describe (Florence-2) → rewrite caption into an *audio* prompt → generate ambience bed (ACE-Step 1.5) + authored dialogue (Chatterbox) → dialogue-anchored mix → stems + manifest → re-mux into `dubbed.mp4`. MIT-publishable lane end to end. Runs on Comfy Cloud today; a local 5090 lane is unbuilt.

Repo: https://github.com/mcp-tool-shop-org/fx-dub · local `E:\AI\fx-dub` · branch `main`, clean, CI green.

**Design is locked and externally verified** — [`docs/design/2026-08-21-fxdub-v1.dispatch.md`](docs/design/2026-08-21-fxdub-v1.dispatch.md), 45 findings, decisions A–J, prism receipt `prism-01m0k6mbv7sh918mhja9bxpszt` (Ed25519, `signature_valid: true`) committed in-repo. **Do not re-litigate A–J without new evidence.**

## 2. THE PIPELINE IS DONE. THE VOICES ARE NOT.

**fx-dub runs end to end and passes its full contract.** Latest run
(`runs/2026-08-22-v27-elevenlabs-final/`, job `11759129-1d01-4d36-9de4-7e055afbd1f4`) scores
**19/19** on `tools/audition_receipt.py`:

- 48 kHz mix at **−18.18 LUFS** (target −18.0 ±2.0)
- dialogue **10.86 LU** above the ambience bed (ducking band is 8–20)
- re-muxed MP4 carries audio, **161 frames intact**, 10.062 s
- caption from mid-clip frame 80, stems + manifests all present

**The one open problem is voice quality.** The Director's verdict, after five engines:
*"None of these sound very natural, and only Brian is anywhere near deep enough."*

⚠ **Do not repeat the mistake that produced that verdict.** I worked down a preset list
instead of going to voice CLONING, and I reached for a cheap post-hoc time-stretch instead of
the premium engine's own controls — after the Director had explicitly said to stop economising.
The standing instruction is in memory as [[feedback-stop-budgeting-credits]]: **buy the good
model, buy options, never optimise cost.**

### The scene (Director's words — do not rewrite them)

```
VOICE (off-frame, DEEP + gritty):  Hey, how's it going?
MAC   (on-frame, gritty, weary):   Not bad. Can't complain.
VOICE:                             Good to hear, good to hear.
VOICE:                             Hey, tell Charlie I got that thing for him,
                                   whenever he wants to drop by.
```
The off-frame man opens *and* closes, so the MC is listening through the final line — that is
the beat the Director described and it is staged correctly now.

### Next action

**Relay `docs/briefs/2026-08-22-fxdub-11-brief.md`** to the Comfy Cloud in-app agent. It asks
for a measured survey of the *entire* TTS surface (not the first list we found), the full preset
rosters for every engine, the delivery-knob map, a definitive answer on whether `LoadAudio` can
feed `ElevenLabsInstantVoiceClone` / `FishAudioInstantVoiceClone`, and six auditioned candidates
across three engines.

**Cloning is the likely answer.** We proved `LoadAudio` resolves a storage key its COMBO never
lists, so reference audio *can* reach a clone node — which means the Director can supply a real
voice reference instead of us shopping preset lists.

### Assembly recipe, once a voice is chosen

Everything below is measured and works; only the VO source needs swapping.

- **Bed:** ElevenLabs `eleven_sfx_v2`, rain + footsteps-A layered at −4 dB. Storage key
  `d8ef106aaa16af33f449e3097f9d4fe78b42a767e508b0476dd7777e20ddfff3.flac`, −17.20 LUFS, 48 kHz.
  Footsteps A (leather heels on wet concrete) is the Director's pick; B (boots) was rejected,
  and the original "splashing through puddles" take was rejected outright.
- **Mix:** bed on `AudioMix.audio_1` (it adopts audio_1's rate), VO on `audio_2`.
- **Gain-stage from MEASURED stem loudness, never a fixed number.** Engines differ by 8 dB on
  the same line. Working recipe for the ElevenLabs VO: `AudioAdjustVolume −3` on the VO,
  `gain_1_db −12` on the bed → mix −18.18 LUFS, 10.86 LU separation.
- **Caption:** `LoadVideo` → `GetVideoComponents` → `ImageFromBatch(batch_index=80, length=1)`
  → `Florence2Run`. The single-frame pick is mandatory (a batch makes Florence return a LIST
  that `SaveText` cannot write) and frame 80 also describes the scene far better than frame 0.
- **Mux:** `VHS_VideoCombine`, `frame_rate` 16 literal, `images` straight from
  `GetVideoComponents`.
- **Verify:** `python tools/audition_receipt.py <dir> --bed-gain-db <N>`. A `bed_lufs` manifest
  is REQUIRED — R128 gates a quiet bed out of the mix master, so ducking depth is unmeasurable
  without a meter on the bed stem.

### Re-mixing is free

`LoadAudio` + storage keys means any remix is deterministic and costs nothing — no regeneration.
Pull stem keys from `get_output` and rebuild. Every mix in session 3 after the first was done
this way.

## 3. What the audition answers

- **The open mix-bus sample rate.** Nobody can answer it without a run: there is no sample-rate-conversion node on the allowlist, `AudioStandardize` conforms channels only, and `AudioMix`'s rate-reconciliation policy is undocumented. The receipt decodes the FLAC headers and settles it. Fold the answer into `kb/build_db.py` **and** the next readouts `model-knowledge` wave.
- Whether the dubbed MP4 actually carries an audio track (the worst failure mode, and the easiest to miss).
- Whether `-18 LUFS` and the dialogue-to-bed offset land where the standards predict.
- What `GetVideoComponents`' framerate FLOAT reports versus our pinned 16.0 — after which the pin can become a derived value for general footage.

## 4. Graph inventory

**The working pipeline is hand-authored API JSON submitted via `submit_workflow`, not a saved
cloud tab.** That was the right call for iteration speed — `dry_run: true` validates free, and
an advisor session can build and run a graph with no in-app-agent round trip — but it means
**v2.3 through v2.7 exist only in the session transcript and in `runs/`**. Promoting the final
recipe to a durable saved workflow is an open action.

| Tab / record | State |
|---|---|
| **v2.3–v2.7 (API JSON)** | The working pipeline, evolved across session 3. v2.7 is current and scores 19/19. Jobs: `35bef893…` (v2.3), `0483fa75…` (v2.3 final), `8b45de73…` (v2.4), `4d10eff7…` (v2.5), `a5c2194d…` (v2.6), `11759129…` (v2.7). Artifacts in `runs/`. **Not yet a saved tab.** |
| `fx-dub v2.2` (34 nodes) | The last saved cloud tab that ran. Superseded by the API-JSON line but still valid; its ACE-Step bed and Chatterbox VO are both retired. |
| `fx-dub v2.1` (34 nodes) | Superseded — its `VHS_LoadVideo` cannot reach the asset namespace. The *archived* file on disk is an older 33-node pre-pin snapshot. Do not mutate. |
| `fx-dub v2.1-turbo` (34 nodes) | Verified three-value delta from v2.2 (`unet_name` → turbo, `steps` 8, `cfg` 1). **Never run** — and now largely moot, since ACE-Step is retired from the bed path. |
| `fx-dub v2` record `65a063a5-9342-4297-8cfa-01313178fab9` | Archival copy restored after the agent's `open_workflow` clobbered the original. Don't touch. |
| `Motif builds v2` record `78a76ecd-7ae2-452a-afea-ad55a8d290f8` | Measured ACE-1.5 reference stack. **Read-only.** |

### Model decisions that changed in session 3

- **ACE-Step 1.5 is RETIRED from the ambience path.** It is a *music* model; asking it for rain
  produced a bed at −39.29 LUFS that the Director could not hear at all. **ElevenLabs
  `eleven_sfx_v2` is the SFX/ambience engine** — 48 kHz stereo at exactly the requested
  duration, with a `loop` flag. `stable_audio_3_small_sfx` is an untested alternative.
- **Prompt SFX with positive claims only.** "Splashing through puddles" got puddles; the fix was
  "hard leather heels striking damp solid stone", not "no splashing" — negation collapses to
  0.2–1.1% accuracy in audio-text models (arXiv:2607.12290, our own study-swarm finding 15).

## 5. Second approved workstream: prompt-craft `domains/audio`

The Director approved (2026-08-21) replacing the hand-wavy half of **decision D** with a real mechanism: a typed contract of *audible* claims, used once to write the audio prompt and once to verify the generated audio.

The study-swarm is **done** — 4 retrieval-backed lanes, 33 findings, written up in [`docs/design/2026-08-21-promptcraft-audio-domain.dispatch.md`](docs/design/2026-08-21-promptcraft-audio-domain.dispatch.md) with a proposed architecture A1–A7.

**Three things the next session must know:**

1. **⚠ The citations are NOT externally verified yet.** Run `roleos verify-citations` → prism on that dispatch (the fx-dub v1 dispatch shows the exact command and receipt shape) **before any finding becomes canon.** Its own standards table scores EXTERNAL_VERIFIER 1 for this reason.
2. **The headline finding is a prohibition, not a feature:** CLAP-driven best-of-N *provably hacks the verifier* in audio (SCORE, arXiv:2509.19831 — CLAP score +10.8%, perceptual quality +1.4%). So the gate **blocks and escalates**; it does not auto-select. N ≤ 4, composite signals, human checkpoint on persistent failure. Also hard-forbidden at automated tiers: **negated claims** (accuracy collapses to 0.2–1.1%) and **temporal-ordering claims**.
3. **`prompt-craft` carries Director-set fences.** Read `[[prompt-craft-dogfood-swarm-handoff]]` in the canonical memory store before editing that repo — `domains/image/subdomains/sprite/identity_subgate.py` is untouchable. The audio work is purely additive: a new `domains/audio/` package plus one `register` call; `core/` must not change.

Repo state as of this session: `prompt-craft` v1.0.0, `afef25e`, 394 tests, clean tree.

## 6. How this project works (the things that cost us time to learn)

The full trap ledger is `SELECT * FROM traps ORDER BY severity` in `kb/fxdub.db` — 24 entries, all measured. The ones that shape daily work:

- **A checkpoint loader's COMBO is not the catalog.** Split-file diffusion models live under `UNETLoader`/`VAELoader`/`CLIPLoader`. Searching only `CheckpointLoaderSimple` produced a confident, false "those files aren't installed" claim.
- **Diff widget *values*, not just topology.** A build reported "carried over unchanged" had silently changed the Florence task.
- **A bare id or URL is not an instruction.** A job id (billing provenance) is not a workflow id, and a signed output URL cannot reach inputs. Label references as references.
- **Two probes reading different fields aren't a contradiction.** ffprobe read the track (clean 16/1); we read the movie header (`mvhd` timescale 0). Both true. When a derived value could come from either, pin a primitive.
- **`open_workflow` clobbers the focused tab AND its saved file.** New tab only.
- **Video generation dwarfs everything:** ~180 credits for two takes versus ~10–15 for a whole fx-dub audio run. **Never regenerate test footage** — the fixture is standing.
- Editor-valid ≠ API-valid (COMBO values are type-strict); STRING outputs need `SaveText` to reach the manifest; masters go through `SaveAudioAdvanced`; pinned-seed byte-identity is memo-cache-only.

## 7. Tests and the knowledge base

**98 tests, CI green**, `python -m unittest discover -s tests -v`. The suite is not decoration:

- `tests/graph_lint.py` is **the trap ledger made executable** — 7 detectors, each *proven red* against the archived known-bad graphs, with a forward gate asserting v2.1 stays clean and a not-vacuous check so it can't pass by omission.
- `tools/audition_receipt.py` + `tools/media_probe.py` verify a real run; `test_every_check_can_fail` proves every check is falsifiable (it caught four of mine that weren't).
- The suite has already caught two real bugs in our own code.

**`kb/fxdub.db`** is the project memory: nodes, models+licenses, measured runs with full job UUIDs, the graph registry, dialog-thread state, traps, decisions, open actions — every row classed **A** (measured) or **B** (advisory). Source of truth is `kb/build_db.py`; edit the seeds, rerun, commit both. **Never hand-edit the .db.** Start any session with `SELECT * FROM v_open_actions`.

## 8. Not started

Host-side rewrite runner (decision D — now superseded in spirit by the prompt-craft plan) · spot-effects event timeline (needs host-side shot/onset detection; the cloud has no such node) · local 5090 lane · SRT export · npm name `fx-dub` unreserved (no collision found; reserve via the trusted-publishing flow at ship time).

## 9. Ritual

Every session ends by updating §2 and §4 of this file, the `AGENTS.md` snapshot, and the `kb/build_db.py` seeds; rebuilding the db; running the suite; and committing. Dialog rounds are archived in `E:/AI/readouts/model-knowledge/dialogs/comfy-agent/` (`YYYY-MM-DD-fxdub-NN-{brief,reply,verification}.md`) with that folder's thread table updated — that archive is the studio's record, and this repo's `docs/briefs/` holds the outbound copies.
