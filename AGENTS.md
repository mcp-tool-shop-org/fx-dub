# AGENTS.md — start here

You are working on **fx-dub**: video → describe (Florence-2) → rewrite → generated ambience bed (ACE-Step 1.5) + authored dialogue (Chatterbox) → dialogue-anchored mix → stems + manifest → re-muxed `dubbed.mp4`. MIT publishable lane. This file is the ground-running entry for any agent session; it is updated at the end of every working session (that rule is part of the workflow — leave it better than you found it).

**State snapshot: 2026-08-22, session 3 — the pipeline is DONE (19/19); the open problem is voice quality.**

> **Continuing a session?** Read [`HANDOFF.md`](HANDOFF.md) — it carries the live state (what's blocked, what's next, what's approved). This file is the durable manual; that one is the current position.

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
8. **Verifying a run:** download the artifacts into one directory, then `python tools/audition_receipt.py <run_dir> --json receipt.json`. It measures the FLAC masters (settling the 48 kHz question), parses both LUFS manifests, checks the dialogue-to-bed offset, confirms the dubbed MP4 carries **both** a video and an audio track with frames intact, and exits non-zero on any contract violation. Every check cites the dispatch choice or trap it traces to. **A failing check is a finding — report it; never tune the thresholds to make it green.**
9. **Tests are a hard gate** (studio feedback memory: tests land in the SAME commit as the code they touch — no "circle back later"). Run `python -m unittest discover -s tests -v` before any push; CI (`.github/workflows/ci.yml`) runs the same on every push touching kb/workflows/tests/assets. The detectors in `tests/graph_lint.py` ARE the executable trap ledger — proven red against the archived known-bad graphs; when a new trap is earned, add its detector + a red-gate fixture in the same commit. When "fx-dub v2.1" is pulled, drop it in `workflows/comfy-cloud/as-built/fx-dub-v2.1.json` — a forward-gate test automatically asserts all detectors stay quiet on it.

## Where things stand (2026-08-22 end of session 3)

- **THE PIPELINE IS COMPLETE AND PASSES ITS CONTRACT.** Latest run `runs/2026-08-22-v27-elevenlabs-final/` scores **19/19** on `tools/audition_receipt.py`: 48 kHz mix at −18.18 LUFS, dialogue 10.86 LU above the bed, re-muxed MP4 carrying audio with 161 frames intact.
- **THE OPEN PROBLEM IS VOICE QUALITY, AND ONLY THAT.** Director's verdict after five engines and 30+ preset voices: *"None of these sound very natural, and only Brian is anywhere near deep enough."* Next action is `docs/briefs/2026-08-22-fxdub-11-brief.md` — a measured survey of the whole TTS surface plus a definitive answer on premium voice **cloning**.
- **Model decisions that changed:** ACE-Step 1.5 is **retired from the ambience path** (it is a *music* model; its rain bed metered −39.29 LUFS and was inaudible). **ElevenLabs `eleven_sfx_v2`** is the SFX engine and **`ElevenLabsTextToSpeech` (`eleven_v3`)** is the voice tier — both 48 kHz, and the TTS has a native `speed` control so no time-stretching is ever needed.
- **Two platform constraints are dead:** `LoadAudio` resolves a cloud storage key its COMBO never lists (proved by an exact round-trip), so **re-mixing is free and deterministic** and **reference audio can reach a clone node**. Voice cloning is confirmed working on cloud.
- **The graphs are hand-authored API JSON**, submitted via `submit_workflow` with `dry_run` for free validation — no in-app-agent round trip needed. v2.3–v2.7 therefore exist only in `runs/` and the transcript; promoting v2.7 to a saved tab is an open action.
- **Tests:** 104 passing, CI green.
- **Not started:** spot-effects timeline, local-lane graphs, npm reservation, prompt-craft `domains/audio`.

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
