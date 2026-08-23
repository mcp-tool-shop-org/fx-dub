# fx-dub round 16 — verification (ours)

Paired with [`2026-08-23-fxdub-16-reply.md`](2026-08-23-fxdub-16-reply.md). Outbound: round 17.

**Round scoreboard: our defects 0, the agent's 0.** A clean closeout. The relay phase ends here and
the build moved to our side; everything below was measured by us, from completed jobs.

## 1. What the agent accepted, and one thing it gave us unprompted

It confirmed the standing state exactly as we recorded it — sync build ours, extract skipped, no
canvas touched, one read-only schema call, all untouchables intact — and accepted both corrections
in its own name. It also restated the durable form of the round-15 lesson better than we did:

> *"Establishing which pipe a job runs through before assigning it is worth more than any single
> schema fact in this thread."*

Adopted as written.

Its four read-for items are answered in round 17 from completed jobs. Nothing it asserted in this
round was contradicted by the run.

## 2. The run happened — five jobs, two paid

| Job | What | Cost |
|---|---|---|
| `aba137d3-fb5e-4365-94fc-cf23cab04640` | frame extract 20/60/120 | free |
| `12b8cab4-c91f-4693-8569-e3b87b7ba47c` | sync.so probe, `cut_off` | ~58 cr |
| `950bd9c4-94a2-46f7-941d-5d064842c764` | MAC positioned stem | free |
| `f8bbdb6b-58ee-47d0-affd-8395eb9fe2f4` | MAC full-length stem, 10.0625 s exact | free |
| `4b2339b4-804a-42aa-8198-e2bf89877803` | sync.so full pass, `silence` | ~403 cr |

**Answered, all from completed jobs:** the five dotted `model.*` slot names were accepted exactly as
advertised (no round-11 divergence — that trap is per-node, not a property of
`COMFY_DYNAMICCOMBO_V3`); `LoadVideo`, `LoadAudio` and `SyncLipSyncNode.video` all resolved cloud
storage keys with **no upload**; `cut_off` returned the shorter track exactly per tooltip.

**The sync is correct.** Mouth articulating at 2.5 s inside MAC's line; mouth **closed** at 7.5 s
while VOICE speaks off-frame. Coordinate targeting at (348, 122) held.

## 3. The finding that changes a design we had already written

`SyncLipSyncNode` **re-times the picture**: 161 frames / 16.000 fps in, **473 frames / ~47 fps** out
across the same 10.0625 s. Confirmed twice (the 1.4375 s probe returned 68 frames). Duration
(10.0625 s, exact) and resolution (832 × 480) survive; frame count does not.

Our planned `fxdub-sync` receipt asserted *"161 frames intact."* **That check would have failed on
every sync.so output regardless of correctness.** It now verifies duration, resolution and
audio-track survival, and treats frame count as re-derived. → open action.

## 4. Two defects of ours the run exposed

**4.1 The stem we told the agent to use was wrong.** Round 14 §2 asserted MAC's ByteDance render
"already carries the leading silence written in." The cloud key `d7ba748c…` decodes to **1.415 s
with no leading silence** — we inferred it from a *local* 4.032 s file and assumed same artifact.
Under `silence` the pad lands at the tail, so the mouth would have moved at **0.0–1.415 s instead of
2.279–3.694 s**: green, well-framed, well-synced, line in the wrong place. The Director's call to
probe first caught it before the ~403 cr run.

Fixed by building the driving track to **exactly** the picture duration (483,000 samples / 48 kHz =
10.0625 s, delta 0.0000 s), which also **eliminated** the `silence` pad-direction unknown rather
than buying the answer.

**4.2 The Florence caption hallucinated a person.** The delivered run's `caption_00001.txt` reads
*"two men standing in a city at night, facing each other."* Decoded frames 20/60/120 show **one man,
facing camera**, and the Director confirmed the second man is off camera the entire clip. That
caption is the semantic intermediate feeding the ambience prompt and **nothing in the pipeline
checks it against the picture**. Two of our own round-12 claims die with it — the "two men facing
each other" framing and the "profile faces at 480p" risk. → open action.

## 5. Two platform findings relayed in round 17

- `SaveVideo.codec.encoding` crashes local pre-flight (`candidate.toLowerCase is not a function`) —
  its options are **objects**, not strings.
- `ImageFromBatch` **clamps an out-of-range `batch_index` silently**, returning the last frame; and
  `GetVideoComponents` decodes at the source rate (161 frames / 16 fps) even from a 473-frame
  container. Caught only because two requested indices returned identical content hashes.

## 6. Record discrepancy opened

`d7ba748c…` is 1.415 s, but the delivered mix's MAC line spans 2.279–3.959 s ≈ 1.68 s by diarized
word timings. The take `HANDOFF.md` names as the shipped MAC is **not** the one in the delivered
mix. → open action.

## 7. State after this round

Traps **74 → 81**, runs **22 → 27**, open actions **15 → 19**. The lip-synced picture is at
`runs/2026-08-23-fxdub19-lipsync/lipsync_final.mp4`; it currently carries only MAC's isolated
positioned track, so re-muxing the shipped mix onto it is the next step and is recorded as an open
action.
