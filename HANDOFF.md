# fx-dub — session handoff

**PASTE TARGET:** a fresh Claude Code session working in `E:\AI\fx-dub`. You are both advisor and executor. The Director is **Mike**; his live word overrides everything here. Never wrap a session the Director didn't end.

**Written 2026-08-22 at the end of session 4 (supersedes all earlier text).** Read [`AGENTS.md`](AGENTS.md) first — it is the durable operating manual — then this file for live state, then query `kb/fxdub.db`.

> **Verify from receipts and pulled artifacts, never from reports.** That rule has now caught a refuted agent claim, a silent CFG defect, a clobbered file, a phantom line of dialogue, and — four times — a wrong conclusion of *ours*. **This document is testimony. Re-verify anything load-bearing against live ground truth before acting on it.**

---

## 0. Thirty seconds

**fx-dub is finished and shipped.** The dub is delivered and accepted; the package is on PyPI; the site, handbook and knowledge base are live. Nothing is blocked and nothing is half-done.

```bash
./verify.sh          # the single gate: tests + build + install-smoke
python kb/build_db.py    # rebuild the project DB from seeds
```

| | |
|---|---|
| Version | **v1.0.1** — [PyPI](https://pypi.org/project/fx-dub/) · [Releases](https://github.com/mcp-tool-shop-org/fx-dub/releases) |
| Tests | **171**, CI green on 3.10 + 3.12 |
| Traps recorded | **65** in `kb/fxdub.db` |
| Site | https://mcp-tool-shop-org.github.io/fx-dub/ · [handbook](https://mcp-tool-shop-org.github.io/fx-dub/handbook/) · [llms.txt](https://mcp-tool-shop-org.github.io/fx-dub/llms.txt) |
| Shipcheck | all hard gates pass, 23 checked / 0 unchecked |

If you do nothing else, read **§3** — those four rules are where all the time went.

## 1. What fx-dub is

Two things, and the second is the shipped product:

1. **A ComfyUI-Cloud dubbing pipeline.** Video → describe (Florence-2) → audio prompt → generated ambience bed + authored dialogue → dialogue-anchored mix → stems + manifests → re-muxed `dubbed.mp4`.
2. **A verification package.** `pip install fx-dub` gives two receipts — one for the audio *container*, one for what was actually *said*. Zero runtime dependencies, no network egress.

The second exists because the first taught us that container metrics cannot see content defects. Design is locked and externally verified: [`docs/design/2026-08-21-fxdub-v1.dispatch.md`](docs/design/2026-08-21-fxdub-v1.dispatch.md), 45 findings, prism receipt `prism-01m0k6mbv7sh918mhja9bxpszt` (Ed25519, `signature_valid: true`). **Do not re-litigate decisions A–J without new evidence.**

## 2. The delivered dub

`runs/2026-08-22-v28-bytedance/` — **19/19** container checks, **11/11** content checks.

- 48 kHz mix at **−18.09 LUFS** · dialogue **+11.17 LU** over the bed
- re-muxed MP4 carries audio, **161 frames**, 10.069 s
- caption from mid-clip frame 80; stems + all three LUFS manifests present

### The scene (the Director's words — do not rewrite them)

```
VOICE (off-frame, DEEP + gritty):  Hey, how's it going?
MAC   (on-frame, gritty, weary):   Not bad. Can't complain.
VOICE:                             Good to hear, good to hear.
VOICE:                             Hey, tell Charlie I got that thing for him,
                                   whenever he wants to drop by.
```

The off-frame man opens **and** closes, so MAC is listening through the final line. Staged correctly; do not re-cut. Machine-readable at [`docs/scenes/night-street.json`](docs/scenes/night-street.json).

### Reproducing it

| Character | Source | Storage key |
|---|---|---|
| VOICE (deep) | ByteDance cast take, re-spoken via **same-engine audio reference**, 3 lines at scene timestamps, seed 502 | ref `0597c19d…`, render `cb457cf0…`, MAC's bleed excised → `b7066f85…` |
| MAC (gritty) | ByteDance text-only, acoustic grit brief, pitch 0, seed 601 | take `37d38cda…`, spliced to close a 1.880 s pause → `d7ba748c…` |
| VO assembled | MAC placed at 2.30 s into the VOICE track | `8eadf234…` |
| Bed | ElevenLabs `eleven_sfx_v2`, rain + footsteps-A at −4 dB, −17.20 LUFS | `d8ef106a…` |
| Clip | 161 frames, 10.0625 s, 16 fps, no audio track | `ea68c5aa…` |

**Re-mixing is free.** `LoadAudio` resolves a storage key its COMBO never lists, so any remix is deterministic with no regeneration. Pull keys from `get_output`.

**Known and accepted:** the last line's tail is clipped — the VOICE render's `[6.3s:9.8s]` timestamp ended the take at 9.840 s, so the decay on "drop by" was never generated. The mix is 10.000 s and the picture is 10.062 s, so there is room. Director: *"Cuts him off at the end, but it's good enough."*

## 3. The four rules that cost the most

**Read these before you touch the pipeline.** Each was paid for in a rejected take or a failed job.

### 3.1 Cast once → lock the take → perform from it

Prompt-designed voice generation is non-deterministic **regardless of seed**. A voice the Director approves **cannot be recalled** by re-running the same prompt — you get a different person.

Once a take is approved, keep the AUDIO. Reference it (same engine) or splice it verbatim. **Never re-render an approved character.** Cross-engine cloning does not preserve identity either — a ByteDance voice cloned into ElevenLabs came back approximated and was rejected by ear.

The Director's words when this went wrong: *"This is all shit if you have no control."* He was right.

### 3.2 Gain-stage from the meter, never from remembered numbers

Two engines measured **6.7 dB apart** on the same line — ElevenLabs −18.34 LUFS, ByteDance −25.03. Reusing the previous recipe's fixed gain after an engine swap buries the dialogue while every container check stays green.

Measure the stem, then compute. Worked example from the delivery run: VO `+7 dB`, bed `gain_1_db −12` → mix −18.09, separation +11.17. Both inside contract, first try.

### 3.3 A `dry_run` PASS is not proof

Pre-flight validates node existence, link integrity and required-input presence against a **bundled catalog that can lag the cloud**. It does *not* validate dotted auto-grow / dynamic-combo slot **names**. Two shapes passed `dry_run` and then failed at execution (`files.item_1`, `model.voices.item_1`).

**Only a completed job proves a graph.** This is our defect, recorded as such.

### 3.4 Container metrics cannot see content

Sample rate, duration and LUFS all passed green on two VO stems the Director rejected within seconds — one carried a line nobody scripted, the other held a 1.880 s hole mid-sentence.

**Run both receipts on every VO.** `tools/dialogue_receipt.py` exists because of those two takes; `--only-speaker` on a per-character stem is the mode that catches a model inventing the other character's lines.

## 4. Open work, in priority order

Full list: `SELECT * FROM v_open_actions;`

| Priority | Item | Owner |
|---|---|---|
| **1** | **Gate the prompt-craft audio-domain dispatch's citations** through `roleos verify-citations` → prism **before any finding becomes canon**. Its own standards table scores EXTERNAL_VERIFIER 1 for exactly this reason. | next session |
| **2** | **Build prompt-craft `domains/audio`** per [`docs/design/2026-08-21-promptcraft-audio-domain.dispatch.md`](docs/design/2026-08-21-promptcraft-audio-domain.dispatch.md) (A1–A7). Additive only: a new `domains/audio/` package plus one `register` call; `core/` must not change, and `domains/image/subdomains/sprite/identity_subgate.py` is untouchable. | next session |
| **3** | Recover the clipped tail (§2). One line, same reference, window opened to ~10.0 s, splice in, re-run both receipts. Polish, not a blocker. | next session |
| 4 | Fold session-4 measurements into the next readouts `model-knowledge` wave — the 16-node/5-engine `partner/audio` inventory, `eleven_v3` audio tags proven working, ByteDance absolute-timeline timestamps, reference content bleed, broken `AudioPad`, cross-engine clone identity loss. | advisor |
| 5 | Extend `dialogue_receipt` to the assembled **mix**. Today's 11/11 is measured on the VO stem — that is the honest scope; diarization on a bed-heavy mix is unverified. | future |
| 6 | Spot-effects event timeline · local-GPU (5090) lane · host-side rewrite runner (decision D, superseded in spirit by the prompt-craft plan). | future |

**Already retired, so you won't find them in `v_open_actions`:** the v2.2-vs-v2.1-turbo ACE-Step A/B and archiving those tabs. **ACE-Step is retired from the ambience path** — it is a *music* model whose rain bed metered −39.29 LUFS and was inaudible to the Director; ElevenLabs `eleven_sfx_v2` replaced it. Both actions were closed as superseded in session 4 rather than left to be chased. They are noted here only because earlier handoffs listed them as live.

## 5. How this project works

- **Both receipts, always.** `audition_receipt.py` for the container, `dialogue_receipt.py` for content. A take can pass the first and be unusable.
- **A failing check is a finding.** Report it; never tune a threshold. Two checks have been *corrected* rather than tuned — both because they measured the wrong quantity, and the reasoning is in their docstrings.
- **When a trap is found, the SAME commit adds the detector, the `kb/build_db.py` seed, and the test.** Not "circle back later." Session 4 found seven traps and wrote none down until the Director asked *"are you using the tools of the repo?"* — don't repeat that.
- **Graphs are code.** `tools/vo_graphs.py` builds the seven VO shapes and every builder is linted by `graph_lint.API_DETECTORS`. Do not hand-type API JSON into a chat window; v2.3–v2.7 were authored that way and are unrecoverable.
- **Isolate unproven nodes into their own job.** ComfyUI does not persist the outputs of nodes that completed before an error, so one bad node loses everything. That rule is why a broken `AudioPad` cost nothing.
- **You can author and run graphs directly.** `submit_workflow` takes hand-authored API JSON; no in-app-agent round trip is needed to test a hypothesis. In round 11, four of five briefed questions were answerable advisor-side in minutes — and the round trip returned an answer that would have deleted a working route (see [`docs/briefs/2026-08-22-fxdub-11-verification.md`](docs/briefs/2026-08-22-fxdub-11-verification.md)).
- **Briefs name their paste target on line 1.** The Director relays by hand; an unlabelled paste lands in the wrong session. Three document kinds live in `docs/briefs/` with different contracts — `*-brief.md` (outbound, names a target), `*-verification.md` (ours, never does), `*-reply.md` (the agent's words, never does, and **may never be archived without a paired verification**).

## 6. The package

`pip install fx-dub` — Python 3.10+, MIT, **zero runtime dependencies**, PyPI via Trusted Publishing (OIDC; workflow `release.yml`, environment `release`, no long-lived token exists).

Modules live in `tools/`; `pyproject.toml` maps that directory onto the `fxdub` import name at build time, so `python tools/audition_receipt.py` keeps working in-repo while the wheel exposes `fxdub.audition_receipt`. **Do not move them.**

Two CI-enforced invariants, both easy to break by accident:

- the runtime dependency list must stay **empty** — `SECURITY.md` and the landing page both promise no network egress;
- `pyproject.toml`'s version must equal the release tag, or `release.yml` fails the publish.

⚠ `tomllib` is **3.11+**. The CI matrix includes the 3.10 floor. A test that imports it goes red on 3.10 while 3.12 stays green — that has happened once already.

## 7. Tests and the knowledge base

**171 tests**, `python -m unittest discover -s tests`. The suite is not decoration:

- `tests/graph_lint.py` is the trap ledger made executable — two registries (`DETECTORS` for editor-format graphs, `API_DETECTORS` for the hand-authored API graphs), each detector **proven red** against the graph that actually failed and silent on the graph that ran.
- `tools/audition_receipt.py` + `tools/dialogue_receipt.py` verify a real run; `test_every_check_can_fail` proves every check is falsifiable — it caught four of mine that weren't.
- The suite has caught real bugs in our own code, including two found while writing tests for it.

**`kb/fxdub.db`** is the project memory: nodes, models, measured runs with full job UUIDs, the graph registry, dialog-thread state, **65 traps**, decisions, open actions — every row classed **A** (measured) or **B** (advisory). Source of truth is `kb/build_db.py`: edit the seeds, rerun, commit both. **Never hand-edit the .db.** Start any session with `SELECT * FROM v_open_actions;`.

## 8. Ritual

Every session ends by updating this file, the `AGENTS.md` snapshot and the `kb/build_db.py` seeds; rebuilding the db; running `./verify.sh`; and committing. Dialog rounds are archived in `E:/AI/readouts/model-knowledge/dialogs/comfy-agent/` (`YYYY-MM-DD-fxdub-NN-{brief,reply,verification}.md`) with that folder's thread table updated — that archive is the studio's record, and this repo's `docs/briefs/` holds the copies.
