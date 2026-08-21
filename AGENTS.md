# AGENTS.md — start here

You are working on **fx-dub**: video → describe (Florence-2) → rewrite → generated ambience bed (ACE-Step 1.5) + authored dialogue (Chatterbox) → dialogue-anchored mix → stems + manifest → re-muxed `dubbed.mp4`. MIT publishable lane. This file is the ground-running entry for any agent session; it is updated at the end of every working session (that rule is part of the workflow — leave it better than you found it).

**State snapshot: 2026-08-21, session 1 (scaffold + rounds 1–4 of the build dialog).**

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
8. **Tests are a hard gate** (studio feedback memory: tests land in the SAME commit as the code they touch — no "circle back later"). Run `python -m unittest discover -s tests -v` before any push; CI (`.github/workflows/ci.yml`) runs the same on every push touching kb/workflows/tests/assets. The detectors in `tests/graph_lint.py` ARE the executable trap ledger — proven red against the archived known-bad graphs; when a new trap is earned, add its detector + a red-gate fixture in the same commit. When "fx-dub v2.1" is pulled, drop it in `workflows/comfy-cloud/as-built/fx-dub-v2.1.json` — a forward-gate test automatically asserts all detectors stay quiet on it.

## Where things stand (2026-08-21 end of session 1)

- **Design:** locked and verified (dispatch + Ed25519 citation receipt in `docs/design/`).
- **Graphs:** the agent's v1 + v2 are archived with defect ledgers. v2's cloud file got clobbered by the agent's `open_workflow`; we restored it from our archive to workflow record **`65a063a5-9342-4297-8cfa-01313178fab9`**. The measured ACE reference stack is record **`78a76ecd-7ae2-452a-afea-ad55a8d290f8`** ("Motif builds v2") — read-only.
- **Live thread:** round-4 brief (GO for "fx-dub v2.1" in a new tab; fixes F1–F6) awaits the Director's relay; then pull + verify + Director's audition run (~10–15 cr) which also closes the open mix-bus sample-rate question.
- **Not started:** host-side rewrite runner (decision D), spot-effects timeline, local-lane graphs, npm reservation.

## Cost intuition (measured)

Caption ≈ 1.8 cr · 10 s bed ≈ 2.0 cr · dialogue line ≈ 1.7 cr · full 30 s clip ≈ 8–12 cr. Cloud rate ≈ 0.266 cr/gpu-sec on rtx_pro_6000.
