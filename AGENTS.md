# AGENTS.md — start here

You are working on **fx-dub**: video → describe (Florence-2) → rewrite → generated ambience bed (ACE-Step 1.5) + authored dialogue (Chatterbox) → dialogue-anchored mix → stems + manifest → re-muxed `dubbed.mp4`. MIT publishable lane. This file is the ground-running entry for any agent session; it is updated at the end of every working session (that rule is part of the workflow — leave it better than you found it).

**State snapshot: 2026-08-22, session 4 — the DUB IS DELIVERED. v2.8 scores 19/19 with Director-approved voices, and the content verifier that was missing now exists.**

> **Continuing a session?** Read [`HANDOFF.md`](HANDOFF.md) — it carries the live state (what's blocked, what's next, what's approved). This file is the durable manual; that one is the current position.

## fx-dub is now a published package

`pip install fx-dub` — Python 3.10+, MIT, **zero runtime dependencies**, published
to PyPI via Trusted Publishing (OIDC; workflow `release.yml`, environment
`release`, no long-lived token anywhere). Two console scripts: `fxdub-receipt`
(container) and `fxdub-dialogue` (content).

The modules still live in `tools/` — `pyproject.toml` maps that directory onto the
`fxdub` import name at build time, so `python tools/audition_receipt.py` keeps
working in-repo exactly as this file describes while the wheel exposes
`fxdub.audition_receipt`. **Do not move them.**

**`./verify.sh` is the single gate**: test suite + wheel/sdist build + install the
wheel into a throwaway venv and exercise it. CI runs exactly this, so green
locally means green in CI. Run it before any push.

Two invariants CI enforces that are easy to break by accident:
- The runtime dependency list must stay **empty** — `SECURITY.md` and the landing
  page both promise no network egress, and a single transitive dep could give the
  lie to that. CI fails the build if `dependencies` becomes non-empty.
- The version in `pyproject.toml` must equal the release tag; `release.yml` fails
  the publish on a mismatch.

## Read in this order

1. This file.
2. The project database: **`kb/fxdub.db`** (SQLite — see queries below; seed source `kb/build_db.py`).
3. [`docs/design/2026-08-21-fxdub-v1.dispatch.md`](docs/design/2026-08-21-fxdub-v1.dispatch.md) — the research-grounded architecture lock (externally verified citations; don't re-litigate decisions A–J without new evidence).
4. [`workflows/comfy-cloud/as-built/README.md`](workflows/comfy-cloud/as-built/README.md) — graph archive + defect ledgers.
5. The latest brief in [`docs/briefs/`](docs/briefs/) — the live build-dialog state.

## The database (future-you's memory)

```bash
python kb/build_db.py                 # rebuild from seed (idempotent)
```
```sql
SELECT * FROM v_open_actions;         -- what's next, right now
SELECT * FROM traps ORDER BY severity;-- the mistakes already paid for
SELECT * FROM v_measured_costs;       -- measured gpu-sec/credits per unit
SELECT * FROM graphs;                 -- every graph, where it lives, its status
SELECT * FROM fts WHERE fts MATCH 'chatterbox';  -- full-text over everything
```
Rows carry `class` **A** (measured on-account: billing feed, API pulls, decoded bytes, `get_node`) or **B** (agent-reported; advisory until measured). Verification dates age per the 30-day freshness rule. **To update knowledge: edit the seed data in `kb/build_db.py`, rerun, commit script + db together.** Never hand-edit the .db.

## Operating rules (earned, not optional)

1. **Verify, don't relay.** The Comfy Cloud in-app agent builds; we pull the graph over the MCP (`get_saved_workflow` — canvas tabs are API-visible), verify wire-by-wire, close costs from `get_billing_activity`, and decode output headers locally. Two of its claims have already been refuted this way (see `traps`).
2. **Validate-only until the Director auditions.** Nothing generates at an unauditioned configuration. Rejected/validated jobs bill zero.
3. **Briefs name their paste target in line 1.** The Director relays them by hand; an unlabeled paste lands in the wrong session.
4. **Version-bump tabs on structural change** (v2 → v2.1), never edit a superseded tab in place. And **never let the in-app agent `open_workflow` in a focused tab** — it clobbers the canvas AND the saved file (it did, once; see `graphs` for the restore).
5. **Full UUIDs in receipts.** Truncated ids have caused real collisions studio-wide.
6. **Archive every round** in the studio dialog folder: `E:/AI/readouts/model-knowledge/dialogs/comfy-agent/` (`YYYY-MM-DD-fxdub-NN-{brief,reply,verification}.md`) and update its thread table. Repo copies of briefs live in `docs/briefs/`.
7. **Session end:** update this snapshot + `kb/build_db.py` seeds + rebuild the db + commit. The wider studio KB (licenses, cloud platform ground truth, 119 models) lives in the readouts monorepo — query `E:/AI/readouts/model-knowledge/models.db`, don't duplicate it here; this db holds only fx-dub-specific truth.
8. **Verifying a run — BOTH receipts, always.** `tools/audition_receipt.py` checks the *container*; `tools/dialogue_receipt.py` checks what was actually *said*. A take can pass the first and be unusable — that has happened twice. For VO, transcribe with `vo_graphs.transcribe()` then `python tools/dialogue_receipt.py docs/scenes/<scene>.json <words>.json [--only-speaker NAME]`; use `--only-speaker` on any per-character stem, since that is the mode that catches a model inventing the other character's lines. Then, for the assembled run: download the artifacts into one directory and `python tools/audition_receipt.py <run_dir> --json receipt.json`. It measures the FLAC masters (settling the 48 kHz question), parses both LUFS manifests, checks the dialogue-to-bed offset, confirms the dubbed MP4 carries **both** a video and an audio track with frames intact, and exits non-zero on any contract violation. Every check cites the dispatch choice or trap it traces to. **A failing check is a finding — report it; never tune the thresholds to make it green.**
9. **Tests are a hard gate** (studio feedback memory: tests land in the SAME commit as the code they touch — no "circle back later"). Run `python -m unittest discover -s tests -v` before any push; CI (`.github/workflows/ci.yml`) runs the same on every push touching kb/workflows/tests/assets. The detectors in `tests/graph_lint.py` ARE the executable trap ledger — proven red against the archived known-bad graphs; when a new trap is earned, add its detector + a red-gate fixture in the same commit. When "fx-dub v2.1" is pulled, drop it in `workflows/comfy-cloud/as-built/fx-dub-v2.1.json` — a forward-gate test automatically asserts all detectors stay quiet on it.

## Where things stand (2026-08-22 end of session 4)

- **THE DUB IS DELIVERED AND ACCEPTED.** `runs/2026-08-22-v28-bytedance/` scores **19/19**: 48 kHz mix at −18.09 LUFS, dialogue **+11.17 LU** over the bed, 161 frames intact, 10.069 s, caption present. Both voices approved by ear.
- **THE VOICE PROBLEM IS CLOSED.** The off-frame man is ByteDance Seed Audio voice-design (pitch −3, cast take `0597c19d…`) re-spoken through **same-engine audio reference**; MAC is ByteDance with an acoustic grit brief, spliced to close a 1.880 s mid-line pause. Neither character was re-rolled after approval — that rule is now load-bearing (see the lesson below).
- **THE MISSING VERIFIER NOW EXISTS.** `tools/dialogue_receipt.py` checks *spoken content* against `docs/scenes/*.json` from a diarized transcript: lines present and ordered, no invented speech, no cross-character overlap, no mid-line straggle, consistent casting, fits the clip. **`audition_receipt.py` cannot see any of that** — it passed green on two takes the Director rejected within seconds. Run BOTH.
- **Model decisions that changed:** ACE-Step 1.5 is **retired from the ambience path** (it is a *music* model; its rain bed metered −39.29 LUFS and was inaudible). **ElevenLabs `eleven_sfx_v2`** is the SFX engine and **`ElevenLabsTextToSpeech` (`eleven_v3`)** is the voice tier — both 48 kHz, and the TTS has a native `speed` control so no time-stretching is ever needed.
- **Two platform constraints are dead:** `LoadAudio` resolves a cloud storage key its COMBO never lists (proved by an exact round-trip), so **re-mixing is free and deterministic** and **reference audio can reach a clone node**. Voice cloning is confirmed working on cloud.
- **The VO graphs are now CODE, not transcript blobs.** `tools/vo_graphs.py` builds all seven shapes (voice design, audio reference, clone+TTS, splice, place, mix, transcribe) and every builder is linted by `graph_lint.API_DETECTORS`, so the shapes that cost real failed jobs cannot be hand-typed back in. v2.3–v2.7 remain unrecoverable — their JSON lived in a session transcript that is gone. **Do not hand-transcribe a replacement and call it as-built.**
- **⚠ `dry_run` is NOT proof.** It validates node existence, link integrity and required-input presence against a bundled catalog. It does **not** validate dotted auto-grow/dynamic-combo slot *names* — two shapes passed `dry_run` and then failed at execution. Only a completed job proves a graph.
- **Tests:** 158 passing, CI green.
- **Not started:** spot-effects timeline, local-lane graphs, npm reservation, prompt-craft `domains/audio`.

## The lesson session 4 paid for

Two defects reached the Director, and **every metric was green for both**: 48 kHz, right duration, clean LUFS. One take carried a fourth line nobody scripted (ByteDance's `audio reference` mode reproduces the reference clip's *dialogue content*, not just its timbre); the other held a 1.880 s pause mid-line that ran into the next character's cue. Container metrics cannot see content. **`tools/dialogue_receipt.py` exists because of those two takes — run it on every VO before the Director hears anything.**

The Director's words when the voices kept changing between renders: *"This is all shit if you have no control."* He was right, and the fix is a rule, not a technique:

> **CAST once → LOCK the approved take → PERFORM every later line from it.**
> ByteDance text-only voice design is non-deterministic *regardless of seed*, so a voice approved in one render cannot be recalled by re-running. Once a take is approved, keep the AUDIO: reference it (same engine) or splice it verbatim. **Never re-render an approved character.** Cross-engine cloning does not preserve identity either — a ByteDance voice cloned into ElevenLabs came back approximated and was rejected.

And the process lesson, in his words: *"Are you using the tools of the repo, because we're dogfooding right now and you're just making quick fixes and not building this out right."* Fifteen graphs had been typed into a chat, seven traps found and none written down, zero detectors added. **When this project finds a trap, the same commit adds the detector, the seed, and the test.** That is the workflow, not an aspiration.

## The lesson session 3 paid for

The Director said *"I have credits to burn, stop budgeting"* — and I still defaulted to the free local TTS, then covered the resulting length problem with a post-hoc `AudioSpeedShift` instead of using the premium engine's own `speed` knob. His response: *"Why are you using cheap techniques when I said that I have credits to burn? Don't waste my time."*

**Reach for the premium engine first. Use its native controls, not post-processing. And when a character voice is wanted, clone a reference — do not shop a preset list.** Standing instruction: [[feedback-stop-budgeting-credits]] in the project memory store.

## The lessons session 2 paid for (read before your next "blocker")

We pulled `get_node("LoadVideo").file`, did not find the agent's asset among the nine options, and told the Director the audition was blocked. **We were wrong.** That COMBO enumerates the *input/attachment* namespace; the clip is a cloud `SaveVideo` output living under a storage key `LoadVideo` resolves but the COMBO never lists. The agent's evidence — the platform validator's `ready_to_run: true` — was the better probe, and we discounted it.

Both halves of the standing rule matter. *Verify, don't relay* — but **absence of evidence in one enumeration is not evidence of absence**, and when our probe and the platform's disagree, the platform is not automatically the one that is wrong. `estimate_credits` cannot arbitrate (it is a pricing pass — it returns 0 credits and no error for a deliberately invalid COMBO value). `get_output(prompt_id)` is the authoritative job→asset mapping. See `traps` in the db; the full account is in `docs/briefs/2026-08-21-fxdub-09-verification.md`.

It happened a second time the same session. We ordered the agent to set `Florence2Run.control_after_generate` to `fixed`; it replied that the node has no such schema input and refused to invent a target. It was right — our own pull confirms the value lives only in `widgets_values`, with no entry in the node's `inputs` array. **The editor graph and the node schema are different views, and a value visible in one is not necessarily settable through the other.** Check the schema before ordering a change to something you only saw in `widgets_values`.

Session scoreboard, kept deliberately: **our defects 3** (the loader "blocker", a truncated round-8 relay, the unactionable `control_after_generate` order); **the agent's 0**. It declared an honest gap in three consecutive rounds and was correct every time. Weigh its reports accordingly — *verify, don't relay* is not *assume wrong*.

## Cost intuition (measured)

Caption ≈ 1.8 cr · 10 s bed ≈ 2.0 cr · dialogue line ≈ 1.7 cr · full 30 s clip ≈ 8–12 cr. Cloud rate ≈ 0.266 cr/gpu-sec on rtx_pro_6000.
