# AGENTS.md — start here

You are working on **fx-dub**: video → describe (Florence-2) → rewrite → generated ambience bed (ACE-Step 1.5) + authored dialogue (Chatterbox) → dialogue-anchored mix → stems + manifest → re-muxed `dubbed.mp4`. MIT publishable lane. This file is the ground-running entry for any agent session; it is updated at the end of every working session (that rule is part of the workflow — leave it better than you found it).

**State snapshot: 2026-08-22, session 2 (rounds 8–10; v2.2 built and cleared for the audition).**

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

## Where things stand (2026-08-22 end of session 2)

- **Design:** locked and verified (dispatch + Ed25519 citation receipt in `docs/design/`).
- **THE AUDITION IS UNBLOCKED.** `fx-dub v2.2` (34 nodes, cloud tab) is built, wire-verified clean, and its loader is **cleared**. Nothing stands between it and the first run but the Director's order (~10–15 cr).
- **Graphs:** v1, v2, v2.1, **v2.2**, and `fx-dub v2.1-turbo` exist. **v2.2 is the audition graph**: `LoadVideo` → `GetVideoComponents` → IMAGE to *both* the Florence branch (`VHS_SelectEveryNthImage(30)`) and `VHS_VideoCombine.images`; `VHS_VideoInfo`/`VHS_LoadVideo` removed; Florence drift fixed (`more_detailed_caption`); all seven prefixes under `fxdub22/`. **v2.1 (34 nodes) is superseded** — its VHS loader cannot reach the asset namespace; the *archived* copy on disk is an older 33-node pre-pin snapshot. `65a063a5-…` is the restored v2 record; `78a76ecd-…` ("Motif builds v2") is the read-only ACE reference stack.
- **The round-6 deferred check is CLOSED:** `PrimitiveFloat` 16.0 → `VHS_VideoCombine.frame_rate` is verified present on input slot 4 (link `718920623009028`; `api_format` resolves to the link, not a literal). ⚠ The widget *under* that link still reads `8` — cut the link and 161 frames silently become a 20.1 s video with no error.
- **Audition fixture — no upload was ever needed.** The clip is already reachable as cloud asset `ea68c5aada3b35b0c8be343f52671cf40ef30066b7d2852766ffe86f1292e5c9.mp4`. We mapped it with `get_output`, downloaded it, and probed it: 161 frames, 10.0625 s, one video track / no audio, sha256 `9985a8ba…` — **byte-identical to `C:/Users/mikey/Downloads/fxdub-audition-clip.mp4`**, and 161/10.0625 = **16.000 fps exactly**. The cloud storage key and the byte sha256 are two addresses for one file. **Do not regenerate test footage**: those video jobs cost ~180 credits versus ~10–15 for a whole audio run.
- **Tests:** 100 passing, CI green. `tests/graph_lint.py` is the executable trap ledger. `docs/briefs/` now carries two document kinds with **opposite** contracts, both enforced: a `*-brief.md` is outbound and must name its paste target on line 1; a `*-verification.md` is advisor-side and must **never** name one (several say the agent was right and we were wrong — pasting one would feed our own reasoning back to the party we are checking). A third test rejects any file in that directory that is neither kind.
- **Live thread: closed through round 10; nothing is outstanding with the agent.** `fx-dub v2.1-turbo` was rebuilt and **verified value-by-value against v2.2: exactly three values differ** — `unet_name` → `acestep_v1.5_xl_turbo_bf16.safetensors`, `steps` 50 → **8**, `cfg` 6 → **1** — all three matching the official `audio_ace_step1_5_xl_turbo` template. Split stack restored, `CheckpointLoaderSimple` gone, 34 nodes, same clip, same seed, same mix bus, `fxdubturbo/` prefixes. **Both graphs are cleared to run together.** Its name lags its lineage (built on v2.2's ingest; the agent has no rename tool) — cosmetic.
- **Two open questions, both deferred to the run, both class B:** whether `FL_ChatterboxTTS` treats `seed: 0` as a literal or a randomize sentinel (agent: "cannot determine" — settle with a repeat run; until then the VO stem is NOT replayable), and what `GetVideoComponents`' fps FLOAT reports against our pinned 16.0.
- **Open design question (Director-raised, NOT yet canon):** adopt `prompt-craft` (MIT, v1.0.0, `E:/AI/prompt-craft`) as the caption→audio-prompt stage. Its `core/plugin.py` explicitly supports new domains by one `register` call, and its tiered verifiers map onto audio (tier 0 = the LUFS/duration checks already in-graph, tier 1 = CLAP-style audio-text alignment, tier 2 = escalate). This would replace the hand-wavy half of decision D. Deliberately not written into the dispatch or the db until the Director rules.
- **Not started:** host-side rewrite runner (decision D), spot-effects timeline, local-lane graphs, npm reservation.

## The lessons session 2 paid for (read before your next "blocker")

We pulled `get_node("LoadVideo").file`, did not find the agent's asset among the nine options, and told the Director the audition was blocked. **We were wrong.** That COMBO enumerates the *input/attachment* namespace; the clip is a cloud `SaveVideo` output living under a storage key `LoadVideo` resolves but the COMBO never lists. The agent's evidence — the platform validator's `ready_to_run: true` — was the better probe, and we discounted it.

Both halves of the standing rule matter. *Verify, don't relay* — but **absence of evidence in one enumeration is not evidence of absence**, and when our probe and the platform's disagree, the platform is not automatically the one that is wrong. `estimate_credits` cannot arbitrate (it is a pricing pass — it returns 0 credits and no error for a deliberately invalid COMBO value). `get_output(prompt_id)` is the authoritative job→asset mapping. See `traps` in the db; the full account is in `docs/briefs/2026-08-21-fxdub-09-verification.md`.

It happened a second time the same session. We ordered the agent to set `Florence2Run.control_after_generate` to `fixed`; it replied that the node has no such schema input and refused to invent a target. It was right — our own pull confirms the value lives only in `widgets_values`, with no entry in the node's `inputs` array. **The editor graph and the node schema are different views, and a value visible in one is not necessarily settable through the other.** Check the schema before ordering a change to something you only saw in `widgets_values`.

Session scoreboard, kept deliberately: **our defects 3** (the loader "blocker", a truncated round-8 relay, the unactionable `control_after_generate` order); **the agent's 0**. It declared an honest gap in three consecutive rounds and was correct every time. Weigh its reports accordingly — *verify, don't relay* is not *assume wrong*.

## Cost intuition (measured)

Caption ≈ 1.8 cr · 10 s bed ≈ 2.0 cr · dialogue line ≈ 1.7 cr · full 30 s clip ≈ 8–12 cr. Cloud rate ≈ 0.266 cr/gpu-sec on rtx_pro_6000.
