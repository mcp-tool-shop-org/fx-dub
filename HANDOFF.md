# fx-dub — session handoff

**PASTE TARGET:** a fresh Claude Code session working in `E:\AI\fx-dub`. You are both advisor and executor. The Director is **Mike**; his live word overrides everything here. Never wrap a session the Director didn't end.

**Written 2026-08-22 at the end of session 2 (supersedes the session-1 text).** Read [`AGENTS.md`](AGENTS.md) first (it is the durable operating manual), then this file (which is the *live state*), then query `kb/fxdub.db`. **Verify from receipts and pulled artifacts, never from reports** — that rule has caught a refuted claim, a silent CFG defect, and a clobbered file in this project alone.

---

## 1. What fx-dub is

Video → describe (Florence-2) → rewrite caption into an *audio* prompt → generate ambience bed (ACE-Step 1.5) + authored dialogue (Chatterbox) → dialogue-anchored mix → stems + manifest → re-mux into `dubbed.mp4`. MIT-publishable lane end to end. Runs on Comfy Cloud today; a local 5090 lane is unbuilt.

Repo: https://github.com/mcp-tool-shop-org/fx-dub · local `E:\AI\fx-dub` · branch `main`, clean, CI green.

**Design is locked and externally verified** — [`docs/design/2026-08-21-fxdub-v1.dispatch.md`](docs/design/2026-08-21-fxdub-v1.dispatch.md), 45 findings, decisions A–J, prism receipt `prism-01m0k6mbv7sh918mhja9bxpszt` (Ed25519, `signature_valid: true`) committed in-repo. **Do not re-litigate A–J without new evidence.**

## 2. THE AUDITION IS UNBLOCKED — order it

Nothing about fx-dub has ever been executed. The first run is the Director's "audition" and it
settles several open questions at once. **As of 2026-08-22 nothing stands in its way but the
order.**

**The graph to run is `fx-dub v2.2`** (cloud tab, 34 nodes) — *not* v2.1, which cannot reach the
clip. It is built, wire-verified clean from the pulled JSON, and its loader is cleared. Cost
~10–15 credits.

**The clip problem is solved, and no upload was ever needed.** Three sessions assumed the fixture
had to be pushed into the inputs folder through the browser. It did not: the clip is *already*
in the cloud asset store, because we generated it there. It is

```
ea68c5aada3b35b0c8be343f52671cf40ef30066b7d2852766ffe86f1292e5c9.mp4
```

which `LoadVideo.file` in v2.2 already points at. We mapped job → asset with
`get_output("1c4e02a8-0a7f-4806-b548-201160f42530")`, downloaded those bytes, and probed them
locally: **161 frames, 10.0625 s, one video track, no audio, sha256 `9985a8ba…` —
byte-identical to `C:/Users/mikey/Downloads/fxdub-audition-clip.mp4`**, and 161 / 10.0625 =
**16.000 fps exactly**, confirming the pin. The cloud storage key and the byte sha256 are simply
two addresses for one file.

**Read this before you doubt the loader again.** We pulled `get_node("LoadVideo").file`, did not
see that hash among its nine options, and told the Director the audition was blocked. **That was
wrong** — the COMBO enumerates the input/attachment namespace, while the clip is a `SaveVideo`
output under a storage key the COMBO never lists. *Absence from an enumeration is not proof of
invalidity*, and when our probe disagrees with the platform's validator, the platform is not
automatically the one in error. `estimate_credits` cannot arbitrate (it is a pricing pass — 0
credits and no error even for a deliberately invalid value). Full account:
`docs/briefs/2026-08-21-fxdub-09-verification.md`.

**Also verified in v2.2, from the links array rather than node presence:** `LoadVideo` →
`GetVideoComponents`; IMAGE to *both* `VHS_SelectEveryNthImage(30)` → `Florence2Run` and
`VHS_VideoCombine.images`; `VHS_VideoInfo` and `VHS_LoadVideo` gone; fps/AUDIO outputs left
unconnected; Florence drift fixed (`more_detailed_caption`); all seven prefixes under `fxdub22/`;
mix bus intact (VO 0 dB / bed −15 dB, meters on mix and VO stem, `ConditioningZeroOut` negative,
shared seed 1, duration 10). **The round-6 deferred check is closed:** `PrimitiveFloat` 16.0 →
`VHS_VideoCombine.frame_rate` sits on input slot 4 (link `718920623009028`) and `api_format`
resolves to the link, not a literal.

⚠ **Latent trap:** the widget *beneath* that link still reads `frame_rate: 8`. The link wins
while it exists; cut it and 161 frames silently render as a 20.1 s video against a 10 s bed, with
no error. The same stale-widget-under-live-link pattern is present and harmless on
`TextEncodeAceStepAudio1.5.duration`, `EmptyAceStep1.5LatentAudio.seconds`, `KSampler.seed`, and
`FL_ChatterboxTTS.text`. **Verify link presence, never widget value.**

**After the run:** download all seven artifacts into one directory and run

```
python tools/audition_receipt.py <run_dir> --json receipt.json
```

It measures 18 checks against the locked contract and exits non-zero on any violation. A failing
check is a finding — report it, never tune the threshold. Commit the receipt.

**Run both tabs.** `fx-dub v2.1-turbo` is rebuilt and verified: exactly three values differ from
v2.2 (`unet_name` → turbo, `steps` 8, `cfg` 1), same clip, same seed, same mix bus,
`fxdubturbo/` prefixes. Running them together gives the cost/quality A/B for the price of one
extra cheap run. **Nothing is outstanding with the agent** — the dialog is closed through round 10.

## 3. What the audition answers

- **The open mix-bus sample rate.** Nobody can answer it without a run: there is no sample-rate-conversion node on the allowlist, `AudioStandardize` conforms channels only, and `AudioMix`'s rate-reconciliation policy is undocumented. The receipt decodes the FLAC headers and settles it. Fold the answer into `kb/build_db.py` **and** the next readouts `model-knowledge` wave.
- Whether the dubbed MP4 actually carries an audio track (the worst failure mode, and the easiest to miss).
- Whether `-18 LUFS` and the dialogue-to-bed offset land where the standards predict.
- What `GetVideoComponents`' framerate FLOAT reports versus our pinned 16.0 — after which the pin can become a derived value for general footage.

## 4. Graph inventory

| Tab / record | State |
|---|---|
| **`fx-dub v2.2` (34 nodes)** | **THE AUDITION GRAPH.** Built, wire-verified clean, loader cleared, never run. Cloud file `fx-dub v2.2.json` (29,884 B). Not yet archived to `workflows/comfy-cloud/as-built/` — do that on the next pull. Open nit: `Florence2Run.control_after_generate` is `randomize` while every other seeded node is `fixed` (submitted seed is 1, so runs are unaffected; canvas replay is not). |
| `fx-dub v2.1` (34 nodes) | **Superseded** — its `VHS_LoadVideo` cannot reach the asset namespace. Wire-verified clean, never run. ⚠ The *archived* file `workflows/comfy-cloud/as-built/fx-dub-v2.1.json` is an older **33-node pre-pin** snapshot, so it lacks the `frame_rate` pin the cloud tab now has. **Do not mutate the tab** — new work goes in new tabs. |
| **`fx-dub v2.1-turbo` (34 nodes)** | **The A/B partner — rebuilt, verified, cleared to run.** Exactly three values differ from v2.2: `UNETLoader.unet_name` → `acestep_v1.5_xl_turbo_bf16.safetensors`, `KSampler.steps` 50 → **8**, `KSampler.cfg` 6 → **1**, all matching the official `audio_ace_step1_5_xl_turbo` template. Split stack restored, `CheckpointLoaderSimple` gone, same clip / seed / mix bus, `fxdubturbo/` prefixes. Name lags lineage (built on v2.2's ingest; the agent has no rename tool) — cosmetic. |
| `fx-dub v2` record `65a063a5-9342-4297-8cfa-01313178fab9` | Archival copy we restored after the agent's `open_workflow` clobbered the original. Don't touch. |
| `Motif builds v2` record `78a76ecd-7ae2-452a-afea-ad55a8d290f8` | The measured ACE-1.5 reference stack. **Read-only.** |
| v1 tabs + demos | Archived with a 10-item defect ledger. Provenance only. |

**The turbo A/B is a verified three-value delta from v2.2.** Same VAE, same dual CLIP, AuraFlow
shift 3, euler / simple / denoise 1, encoder `cfg_scale` 2, shared seed 1, duration 10, identical
Florence block and mix bus, and the same `frame_rate` pin on slot 4. That is a genuinely controlled
comparison — the loader-topology swap round 8 originally asked for was not.

⚠ **Do not hand-transcribe a pulled graph into the as-built archive.** A 30 KB graph is thousands
of numeric node and link ids; one transposed digit yields an archive that silently lies to every
future session. Archiving v2.2 and the turbo tab is an open action and needs a direct
pull-to-disk path, not a copy out of a transcript.

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
