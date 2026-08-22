# fx-dub — session handoff

**PASTE TARGET:** a fresh Claude Code session working in `E:\AI\fx-dub`. You are both advisor and executor. The Director is **Mike**; his live word overrides everything here. Never wrap a session the Director didn't end.

**Written 2026-08-21 at the end of session 1.** Read [`AGENTS.md`](AGENTS.md) first (it is the durable operating manual), then this file (which is the *live state*), then query `kb/fxdub.db`. **Verify from receipts and pulled artifacts, never from reports** — that rule has caught a refuted claim, a silent CFG defect, and a clobbered file in this project alone.

---

## 1. What fx-dub is

Video → describe (Florence-2) → rewrite caption into an *audio* prompt → generate ambience bed (ACE-Step 1.5) + authored dialogue (Chatterbox) → dialogue-anchored mix → stems + manifest → re-mux into `dubbed.mp4`. MIT-publishable lane end to end. Runs on Comfy Cloud today; a local 5090 lane is unbuilt.

Repo: https://github.com/mcp-tool-shop-org/fx-dub · local `E:\AI\fx-dub` · branch `main`, clean, CI green.

**Design is locked and externally verified** — [`docs/design/2026-08-21-fxdub-v1.dispatch.md`](docs/design/2026-08-21-fxdub-v1.dispatch.md), 45 findings, decisions A–J, prism receipt `prism-01m0k6mbv7sh918mhja9bxpszt` (Ed25519, `signature_valid: true`) committed in-repo. **Do not re-litigate A–J without new evidence.**

## 2. THE ONE THING BLOCKING EVERYTHING: the audition run

Nothing about fx-dub has ever been executed. `fx-dub v2.1` is built, verified clean, and has never run. The first run is the Director's "audition" and it settles several open questions at once.

**Live blocker:** the audition clip is not reachable by the graph's loader. The full story, because it is subtle:

- The fixture is a 10-second silent Wan-generated clip: **161 frames, 10.0625 s, 16 fps, h264, one video track, no audio**, `sha256 9985a8ba6197ea7c02adc99c4c3aafc2a9d1cfa13e535ede64908ebea327a30c`. Cross-verified by two independent probes (our MP4 atom walk + the agent's ffprobe). Local copies: `C:\Users\mikey\Downloads\fxdub-audition-clip.mp4`.
- **There is no API path to put video into inputs** — the MCP's `upload_file` is image-only (`.mp4` → `validation.input`), and the in-app agent has no inputs-namespace writer. Confirmed from both sides.
- **There are TWO video namespaces.** `VHS_LoadVideo.video` reads the VHS input folder (measured: only `["bedroom.mp4"]`). Core `LoadVideo.file` reads the asset/attachment namespace (measured: **9 content-addressed `.mp4`s**). The Director's attachment landed in the second and is invisible to the first. This is what defeated three attempts.
- **The way through** (ordered in round 9, awaiting the agent): core `LoadVideo` → **`GetVideoComponents`** (core, `VIDEO → IMAGE + AUDIO + framerate + bit depth`) → the existing IMAGE consumers. This bypasses the VHS folder entirely and is the better architecture anyway, since a published fx-dub takes users' footage via attachment.

**Next action:** relay [`docs/briefs/2026-08-21-fxdub-09-brief.md`](docs/briefs/2026-08-21-fxdub-09-brief.md) if the Director hasn't; the agent must identify *which* of the 9 assets is our clip by probing for 161 frames / 16 fps / 10.0625 s / no audio track — **it must not guess**, and if none match we do not run.

**Then:** pull `fx-dub v2.2`, verify the ingest rewiring wire-by-wire, and — in that same single pull — verify the one thing still deferred: that the `PrimitiveFloat` 16.0 actually lands on `VHS_VideoCombine.frame_rate` and the old `source_fps` link is gone. (Node presence is verified: 34 nodes, node id `421351014920351` = 16.0. The *link* is not.)

**Then the Director orders the run** (~10–15 credits). Afterwards: download all seven artifacts into one directory and run

```bash
python tools/audition_receipt.py <run_dir> --json receipt.json
```

It measures 18 checks against the locked contract and exits non-zero on any violation. **A failing check is a finding — report it, never tune the threshold.** Commit the receipt.

## 3. What the audition answers

- **The open mix-bus sample rate.** Nobody can answer it without a run: there is no sample-rate-conversion node on the allowlist, `AudioStandardize` conforms channels only, and `AudioMix`'s rate-reconciliation policy is undocumented. The receipt decodes the FLAC headers and settles it. Fold the answer into `kb/build_db.py` **and** the next readouts `model-knowledge` wave.
- Whether the dubbed MP4 actually carries an audio track (the worst failure mode, and the easiest to miss).
- Whether `-18 LUFS` and the dialogue-to-bed offset land where the standards predict.
- What `GetVideoComponents`' framerate FLOAT reports versus our pinned 16.0 — after which the pin can become a derived value for general footage.

## 4. Graph inventory

| Tab / record | State |
|---|---|
| `fx-dub v2.1` (33→34 nodes) | **The verified-clean primary.** F1–F6 all pass; zero detector findings. Never run. Archived: `workflows/comfy-cloud/as-built/fx-dub-v2.1.json`. **Do not mutate** — new work goes in new tabs. |
| `fx-dub v2.1-turbo` | Ordered round 8, Director-approved: a **controlled A/B** — identical to v2.1 except the generator block (`ace_step_1.5_turbo_aio` + the *official turbo template's* sampler, read not guessed) and `fxdubturbo/*` prefixes. Status unknown; check the agent's reply. |
| `fx-dub v2.2` | Ordered round 9: the `LoadVideo`+`GetVideoComponents` ingest. Awaiting build. |
| `fx-dub v2` record `65a063a5-9342-4297-8cfa-01313178fab9` | Archival copy we restored after the agent's `open_workflow` clobbered the original. Don't touch. |
| `Motif builds v2` record `78a76ecd-7ae2-452a-afea-ad55a8d290f8` | The measured ACE-1.5 reference stack. **Read-only.** |
| v1 tabs + demos | Archived with a 10-item defect ledger. Provenance only. |

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
