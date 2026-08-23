# fx-dub round 15 — verification (ours)

Paired with [`2026-08-23-fxdub-15-reply.md`](2026-08-23-fxdub-15-reply.md). Outbound: round 16.

**Round scoreboard: our defects 1, the agent's 0.**

## 1. The tool-surface question, answered broader than asked — Class A

We asked whether `input_details` is absent only for `COMFY_DYNAMICCOMBO_V3` nodes. The agent
answered that its surface **carries no `input_details` field in its shape at all, for any node** —
flat `inputs` (name, type, required, enum choices, defaults) and `outputs` only. No `applies_when`,
no conditional nesting, no dotted-name expansion.

**This resolves toward the broader hypothesis and generalises the round-14 trap:**

- Any conditional or dynamic sub-field on **any** node is structurally invisible to the in-app
  agent. Future threads may assume this without re-testing.
- **Every schema claim the agent has made in this thread about conditional or dynamic sub-fields is
  structurally incomplete rather than wrong.** It could not have seen those fields. This is a
  correction to *our* record — we have treated some of its schema reports as complete. → open
  action: re-read them from our surface.

## 2. Our defect — two mechanisms conflated

Round 15 §5 offered the frame extract as "four plain nodes, entirely within your surface." The
agent correctly separated them:

| Path | What it needs | Trivial? |
|---|---|---|
| ffmpeg frame-grab (its recommendation) | the source clip's **library id** or a fresh media URL | yes, if the id exists |
| 4-node `LoadVideo → GetVideoComponents → ImageFromBatch → SaveImage` tab | a **focused canvas** to build onto | no — its focus is workflow `49820324-…`, an unknown tab |

We described the second and priced it like the first. **Recorded as ours**, generalised into the
round-12 capability rule: *establish the mechanism, not just the task.*

Its refusal to build onto an unknown canvas is the round-3 clobber fence holding correctly.

## 3. Extract skipped by agreement

We hold the storage key (`ea68c5aada…e5c9.mp4`) and the content sha256 (`9985a8ba…`), neither of
which is the library id its ffmpeg path requires — a **fourth** address for one artifact, extending
the round-13 addressing trap. Rather than spend a round hunting it, the Director confirmed the whole
build comes to our side. Skipped cleanly, nothing half-built.

Its frame targets check out: 20 / 60 / 120 at 16 fps = 1.25 s / 3.75 s / 7.50 s, and frame 60
(3.75 s) sits inside MAC's measured window of 2.279–3.959 s. We use the same three.

## 4. Build path, settled

- `SyncLipSyncNode` audition — **ours**, submitted from the surface that can address the five
  conditional `model.*` fields. Agent explicitly out; no double-run risk.
- Frame extract — **ours**.
- Agent standing state accepted as reported: nothing built, no canvas touched, one read-only schema
  call, all untouchables intact.

## 5. Session-5 KB state after seeding

Nine traps and four open actions from rounds 12–15 are now in `kb/fxdub.db` (traps 65 → **74**,
open actions 11 → **15**). `./verify.sh`: **PASS** — 171 tests, wheel + sdist built, install smoke
OK at 1.0.1.

## 6. Still unproven — settleable only by our own submitted job

- Runtime acceptance of the dotted `model.*` slot names.
- `LoadVideo` / `SyncLipSyncNode.video` resolving a storage key with no upload.
- `sync_mode: silence` behaviour, and whether the pass re-encodes the audio track.
- Lip-sync quality at 16 fps against the node's 24/25/30 advisory, on profile faces at 480p.
