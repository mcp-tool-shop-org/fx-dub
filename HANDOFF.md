# fx-dub — session handoff

**PASTE TARGET:** a fresh Claude Code session working in `E:\AI\fx-dub`. You are both advisor and executor. The Director is **Mike**; his live word overrides everything here. Never wrap a session the Director didn't end.

**Written 2026-08-23 at the end of session 5 (supersedes all earlier text).** Read [`AGENTS.md`](AGENTS.md) first — it is the durable operating manual — then this file for live state, then query `kb/fxdub.db`.

> **⭐ AMENDED 2026-09-14 (session 6) — v1.2.0 IS SHIPPED.**
> **Version:** v1.2.0 on PyPI (Trusted Publishing, run 34907480151). **Tests: 284**, not the 197 stated below — and `AGENTS.md` said 158 for two sessions before that. Re-measure, don't quote.
> **New:** `fxdub.verify`, the declared public API; `dialogue_receipt` is reimplemented on it.
> **Two defects closed that nothing could see.** (1) A committed receipt carried the operator's absolute path — public repo since v1.0.0, caught by the Phase-0 identity gate, published artifacts always clean. (2) CI ran the matrix twice per commit; four of five duplicate pairs were branch-push + tag-push, so every release paid double. Both have detectors proven red against the real pre-fix bytes. **The v1.2.0 tag fired exactly one CI run — the first release that did.**
> **The carry-forward lesson:** shipcheck 100%, 197 tests and green CI were all true and all insufficient. A defect whose only symptom is extra *success* has no alarm surface. Measure the artifact, never read the config.
> Everything else below still holds.

> **Verify from receipts and pulled artifacts, never from reports.** That rule has now caught a refuted agent claim, a silent CFG defect, a clobbered file, a phantom line of dialogue, a hallucinated second man, and — six times — a wrong conclusion of *ours*. **This document is testimony. Re-verify anything load-bearing against live ground truth before acting on it.**

---

## 0. Thirty seconds

**fx-dub is finished and shipped.** The dub is delivered and accepted, the picture is lip-synced, **v1.1.1 is on PyPI**, and the site, handbook and knowledge base are live. Nothing is blocked.

```bash
./verify.sh                 # the single gate: tests + build + install-smoke
python kb/build_db.py       # rebuild the project DB from seeds
```

Then `SELECT * FROM v_open_actions;` — start there.

| | |
|---|---|
| Version | **v1.1.1** — [PyPI](https://pypi.org/project/fx-dub/) · [Releases](https://github.com/mcp-tool-shop-org/fx-dub/releases) |
| Tests | **197**, CI green on 3.10 + 3.12 |
| Traps recorded | **89** in `kb/fxdub.db` |
| Site | https://mcp-tool-shop-org.github.io/fx-dub/ · [handbook](https://mcp-tool-shop-org.github.io/fx-dub/handbook/) · [llms.txt](https://mcp-tool-shop-org.github.io/fx-dub/llms.txt) |
| Shipcheck | all hard gates pass — 23 checked / 0 unchecked / 14 skipped, re-walked at v1.1.0 |

**One thing is owed to someone else:** the Comfy agent is holding a false claim of ours as fact. See §9 — the next outbound round opens with the retraction.

If you do nothing else, read **§3**. Six rules, and every one was paid for.

## 1. What fx-dub is

Two things, and the second is the shipped product:

1. **A ComfyUI-Cloud dubbing pipeline.** Video → describe (Florence-2) → audio prompt → generated ambience bed + authored dialogue → dialogue-anchored mix → stems + manifests → re-muxed `dubbed.mp4` → *(optional)* lip-sync one named face and re-mux.
2. **A verification package.** `pip install fx-dub` gives two receipts — one for the audio *container*, one for what was actually *said*. Zero runtime dependencies, no network egress.

The second exists because the first taught us that container metrics cannot see content defects. Design is locked and externally verified: [`docs/design/2026-08-21-fxdub-v1.dispatch.md`](docs/design/2026-08-21-fxdub-v1.dispatch.md), 45 findings, prism receipt `prism-01m0k6mbv7sh918mhja9bxpszt` (Ed25519, `signature_valid: true`). **Do not re-litigate decisions A–J without new evidence.**

## 2. The delivered dub

`runs/2026-08-22-v28-bytedance/` — **19/19** container checks, **11/11** content checks.

With `--scene docs/scenes/night-street.json` it is **19/20**: `caption:person_count_matches_cast` fails because the caption claims two men over a one-man shot. That is a real finding about the delivered run, not a regression — the audio is unaffected and the Director accepted the dub.

- 48 kHz mix at **−18.09 LUFS** · dialogue **+11.17 LU** over the bed
- re-muxed MP4 carries audio, **161 frames**, 10.069 s

### The scene (the Director's words — do not rewrite them)

```
VOICE (off-frame, DEEP + gritty):  Hey, how's it going?
MAC   (on-frame, gritty, weary):   Not bad. Can't complain.
VOICE:                             Good to hear, good to hear.
VOICE:                             Hey, tell Charlie I got that thing for him,
                                   whenever he wants to drop by.
```

**One man is on screen for the whole clip.** Director, 2026-08-23: *"One man is off camera the entire clip."* VOICE is never visible — the Florence caption claiming "two men… facing each other" is a hallucination, and it is what feeds the audio prompt. Machine-readable at [`docs/scenes/night-street.json`](docs/scenes/night-street.json), which now declares `on_frame` per character and MAC's measured face at **(348, 122)** on frame 60.

### Reproducing it — proven byte-identical, 2026-08-23

The whole delivered run rebuilds from **three storage keys**, verified at every hop by FLAC STREAMINFO md5 (bytes 18–34 of the block body — no decoder needed, free to check locally):

```
VOICE b7066f85…  +  MAC d7ba748c… placed at 2.30 s
      → assembled VO  8eadf234…            md5 e65dc817…
      → +7 dB (AudioAdjustVolume)          md5 b2816092…  = the delivered stem_vo
      → + bed d8ef106a… at gain_1_db −12   md5 c34976a8…  = the delivered mix
```

| Character | Source | Storage key |
|---|---|---|
| VOICE (deep) | ByteDance cast take, re-spoken via same-engine audio reference, seed 502 | ref `0597c19d…`, render `cb457cf0…`, MAC's bleed excised → `b7066f85…` |
| MAC (gritty) | ByteDance text-only, acoustic grit brief, pitch 0, seed 601 | take `37d38cda…` (3.624 s), spliced to close a 1.880 s pause → `d7ba748c…` (1.415 s) |
| Bed | ElevenLabs `eleven_sfx_v2`, rain + footsteps-A at −4 dB, −17.20 LUFS | `d8ef106a…` |
| Clip | 161 frames, 10.0625 s, 16 fps, 832 × 480, no audio track | `ea68c5aa…` |

Two things this settles. **`AudioMix` cannot apply the +7 itself** — its gains clamp at ±6 dB, so the VO boost is an `AudioAdjustVolume` node ahead of the bus. And **the stems ship at different points in the gain chain**: `stem_vo` is post-gain, the bed stem is pre-gain. That asymmetry is why `audition_receipt` needs `--bed-gain-db`, and why its −9 default reports this run's ducking depth 3 LU low. Pass `-12`.

**Known and accepted:** the last line's tail is clipped — the VOICE render's `[6.3s:9.8s]` timestamp ended the take at 9.840 s, so the decay on "drop by" was never generated. Director: *"Cuts him off at the end, but it's good enough."*

### Lip-synced variant (session 5)

`runs/2026-08-23-fxdub21-remux/dubbed_lipsynced.mp4` — the same dub with MAC's mouth driven to his line, then the shipped mix laid back over it. **832 × 480, 161 frames, 10.0625 s video / 10.0693 s audio, both tracks** — the original contract intact. Receipt **19/20**; `PROVENANCE.md` names which files were carried over from v28 and why that is sound.

- picture: `SyncLipSyncNode` (`sync-3`), `sync_mode: silence`, `speaker_selection: coordinates` at **(348, 122)** on frame 60, seed 42 → key `4ff03353…`. **~403 credits.**
- driving audio: MAC's positioned track built to **exactly** the picture duration → `4afc41d2…`
- mux: `GetVideoComponents → VHS_VideoCombine`, `frame_rate` LINK-driven

Every graph is a builder in `tools/vo_graphs.py`. Do not hand-author these.

## 3. The six rules that cost the most

**Read these before you touch the pipeline.** Each was paid for in a rejected take, a failed job, or a published mistake.

### 3.1 Cast once → lock the take → perform from it

Prompt-designed voice generation is non-deterministic **regardless of seed**. A voice the Director approves **cannot be recalled** by re-running the same prompt. Once a take is approved, keep the AUDIO — reference it (same engine) or splice it verbatim. **Never re-render an approved character.** Cross-engine cloning does not preserve identity either.

**This now applies to the picture too.** `SyncLipSyncNode`'s own tooltip: *"results are non-deterministic regardless of seed."* An approved lip-sync take is kept, never re-rendered.

The Director's words when this went wrong: *"This is all shit if you have no control."* He was right.

### 3.2 Gain-stage from the meter, never from remembered numbers

Two engines measured **6.7 dB apart** on the same line. Reusing the previous recipe's fixed gain after an engine swap buries the dialogue while every container check stays green.

**And a remembered gain is not a recipe.** "VO +7 dB" sat in this handoff for a day — and `AudioMix` cannot do +7, because its gains clamp at ±6. The node that applies it (`AudioAdjustVolume`) was never named, so the recipe was unreproducible as written. **Name the node, not just the number.**

### 3.3 A `dry_run` PASS is not proof

Pre-flight validates against a bundled catalog that can lag the cloud, and does **not** validate dotted auto-grow slot names. Two shapes passed `dry_run` and failed at execution.

**Only a completed job proves a graph.** Corollary earned in session 5: a partner node's real constraints can live only in its **description string**, where the validator cannot see them at all — Kling states 720–1920 px and 2–10 s in prose and would have failed server-side *after* credits committed.

### 3.4 Container metrics cannot see content

Sample rate, duration and LUFS all passed green on two VO stems the Director rejected within seconds.

**Run both receipts on every VO.** And the trap generalises past audio: the pipeline's Florence caption claimed two men over a one-man shot and rode through a whole delivered run green, because no audio check can see a picture. `--scene` closes that specific hole.

The visual domain has the same shape and **no receipt yet**: `SyncLipSyncNode`'s `speaker_selection` defaults to *let the model decide*, so an unpinned graph returns a valid, correctly-framed, right-duration MP4 with the wrong person's mouth moving. A detector fails that graph; nothing measures the output.

### 3.5 Read a node from a second surface before concluding a field is absent

Our `get_node` returns **nine** required inputs for `SyncLipSyncNode` with five conditional `model.*` sub-fields. The in-app agent's surface returns **four** and carries no `input_details` structure at all — for *any* node, confirmed as a general property of its tooling.

Round 11 taught *advertised ≠ runtime*. This teaches **advertised ≠ advertised**. Every schema claim that agent has made about conditional or dynamic sub-fields is structurally incomplete rather than wrong — it could not have seen those fields.

### 3.6 A model's output is evidence, not a measurement

Session 5 read diarized word timings — MAC at 2.279–3.959 s — as a *measurement of the clip's extent*, and used it to rule out a 1.415 s artifact as the shipped take. The clip truly spans **2.300–3.715 s**; the diarizer ran 0.021 s early at the head and **0.244 s late at the tail**.

We published that contradiction into this file, a relayed brief, a released CHANGELOG and the KB **before testing it** — while documenting the caption hallucination, which is the same class of error.

**Word timings gate CONTENT (order, overlap, gaps). They do not establish EXTENT. For extent, decode the file.** The FLAC md5 in STREAMINFO is free and exact; prefer it over any duration match.

## 4. Open work, in priority order

Full list: `SELECT * FROM v_open_actions;` — 16 open.

| Priority | Item | Owner |
|---|---|---|
| **1** | **Open the next Comfy round with the §5.2 retraction** (§9). The agent logged our false claim as its record of our open action. | next session |
| **2** | **Build `fxdub-sync`** — the third receipt, against the **measured** behaviour: verify duration, resolution and audio-track survival. **Do NOT assert frame-count preservation on the raw sync output** (161 → 473); assert it on the deliverable after the mux round-trip. | next session |
| **3** | Gate the prompt-craft audio-domain dispatch's citations through `roleos verify-citations` → prism **before any finding becomes canon**. | next session |
| **4** | Build prompt-craft `domains/audio` per [`docs/design/2026-08-21-promptcraft-audio-domain.dispatch.md`](docs/design/2026-08-21-promptcraft-audio-domain.dispatch.md) (A1–A7). Additive only. | next session |
| 5 | Recover the clipped tail on VOICE's last line. Polish, not a blocker. | next session |
| 6 | Add a `graph_lint` detector for the mux `frame_rate` trap — a builder test exists, a detector does not. | advisor |
| 7 | Re-read from **our** surface any schema claim the in-app agent made about conditional sub-fields (§3.5). | advisor |
| 8 | Fold the session-4 and session-5 measurements into the next readouts `model-knowledge` wave. | advisor |
| 9 | Record the missing session-4 job_ids in `RUNS`. Lower value now that provenance is proven byte-identical. | advisor |
| 10 | Extend `dialogue_receipt` to the assembled **mix**; spot-effects timeline; local-GPU lane. | future |

## 5. How this project works

- **Both receipts, always.** `audition_receipt.py` for the container, `dialogue_receipt.py` for content. A take can pass the first and be unusable.
- **A failing check is a finding.** Report it; never tune a threshold. Two checks have been *corrected* rather than tuned — both because they measured the wrong quantity, and the reasoning is in their docstrings.
- **When a trap is found, the SAME commit adds the detector, the `kb/build_db.py` seed, and the test.** Not "circle back later."
- **Graphs are code.** `tools/vo_graphs.py` builds the VO shapes *and* the picture stage, and every builder is linted by `graph_lint.API_DETECTORS`. **Session 5 hand-typed every lip-sync graph into a chat window anyway — through an entire paid run — and only noticed on opening the file and finding `place()` and `mix()` already there. Open this module before you author a graph.**
- **Isolate unproven nodes into their own job.** ComfyUI does not persist outputs of nodes that completed before an error.
- **You can author and run graphs directly.** `submit_workflow` takes API JSON; no agent round trip is needed to test a hypothesis. In round 11 the round trip returned an answer that would have deleted a working route.
- **Briefs name their paste target on line 1.** Three document kinds live in `docs/briefs/` — `*-brief.md` (outbound, names a target), `*-verification.md` (ours, never does), `*-reply.md` (the agent's words, never does, and **may never be archived without a paired verification** — enforced by `test_docs.py`, which caught this once in session 5).

## 6. The package

`pip install fx-dub` — Python 3.10+, MIT, **zero runtime dependencies**, PyPI via Trusted Publishing (OIDC; workflow `release.yml`, environment `release`, no long-lived token exists).

Modules live in `tools/`; `pyproject.toml` maps that directory onto the `fxdub` import name at build time, so `python tools/audition_receipt.py` keeps working in-repo while the wheel exposes `fxdub.audition_receipt`. **Do not move them.**

Invariants, now enforced in **two** places each:

- the runtime dependency list must stay **empty** — CI *and* `ZeroDependencyTests`, which is itself proven able to go red;
- `pyproject.toml`'s version must equal the release tag, or `release.yml` fails the publish.

⚠ `tomllib` is **3.11+**. The CI matrix includes the 3.10 floor. A test that imports it goes red on 3.10 while 3.12 stays green — that has happened once already.

**Release ordering is not optional.** When the README changes as part of a release, translations run **before** the tag, so the released commit carries source and translations in step:

```bash
node E:/AI/polyglot-mcp/scripts/translate-all.mjs README.md
```

Then stage `README.md README.*.md` together → one release commit → tag → push → CI green → `gh release create` → OIDC publishes. Verify the **published** wheel from the index afterwards, not the local build.

## 7. Tests and the knowledge base

**197 tests**, `python -m unittest discover -s tests`. The suite is not decoration:

- `tests/graph_lint.py` is the trap ledger made executable — each detector **proven red** against the graph that actually failed and silent on the graph that ran.
- `test_every_check_can_fail` proves every receipt check is falsifiable — it caught four that weren't.
- `test_docs.py` caught session 5 archiving an agent reply without its paired verification.
- The suite has caught real bugs in our own code, including two found while writing tests for it.

**`kb/fxdub.db`** is the project memory: nodes, models, measured runs with job UUIDs, the graph registry, dialog-thread state, **89 traps**, decisions, open actions — every row classed **A** (measured) or **B** (advisory). Source of truth is `kb/build_db.py`: edit the seeds, rerun, commit both. **Never hand-edit the .db.**

**When a finding is retracted, REPLACE the trap — do not append a contradiction.** A knowledge base holding both readings is worse than one holding either. Session 5's provenance retraction is the worked example.

## 8. Ritual

Every session ends by updating this file, the `AGENTS.md` snapshot and the `kb/build_db.py` seeds; rebuilding the db; running `./verify.sh`; and committing. Dialog rounds are archived in `E:/AI/readouts/model-knowledge/dialogs/comfy-agent/` (`YYYY-MM-DD-fxdub-NN-{brief,reply,verification}.md`) with that folder's thread table updated — that archive is the studio's record, and this repo's `docs/briefs/` holds the copies.

**That archive is a separate git repo and needs its own commit, scoped to the dialogs directory** — other people's uncommitted work lives in that tree.

## 9. The Comfy agent thread — paused, and we owe it a correction

Rounds 12–17 are archived. The thread is **paused with nothing pending on the agent's side**, and its standing report is clean: nothing built, no canvas touched, all fx-dub tabs untouched, its focus on workflow `49820324-…` which is not ours.

**We owe it a retraction.** Round 17 §5.2 told it *"the take our handoff names as the delivered MAC is not the one in the delivered mix."* That is false (§3.6) and it logged the claim faithfully as our open action. **The next outbound round opens with the correction, before anything else.**

Worth carrying about how this thread runs:

- **The relay flattens node names.** Seven occurrences across rounds 8–15, including inside the message denying it happened. Names never cross this channel authoritatively — re-derive from the live catalog at point of use.
- **Its scoreboard across rounds 12–17 is 1 defect to our 7.** It refused three impossible or circular asks, corrected our Kling premise and our `get_output` type mismatch, separated two mechanisms we had conflated, and flagged its own single error itself. **Take its refusals seriously; they have been right far more often than ours.**
- It cannot address conditional sub-fields on any node (§3.5), so it is out of the build path for `SyncLipSyncNode` and anything else with a dynamic combo.
