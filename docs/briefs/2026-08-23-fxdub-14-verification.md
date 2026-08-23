# fx-dub round 14 — verification (ours)

Paired with the agent's round-14 reply (relayed 2026-08-23, archived as
[`2026-08-23-fxdub-14-reply.md`](2026-08-23-fxdub-14-reply.md)). Outbound response: round 15.

**Round scoreboard: our defects 1, the agent's 0.** Our defect is the round-13/14 diagnosis
("a lean view collapsed them") — wrong, and stated with more confidence than the evidence carried.

## 1. CONFIRMED LIVE DIVERGENCE between tool surfaces — Class A, the finding of the thread

The agent held its ground under a direct challenge and asked for one number: does
`get_node("SyncLipSyncNode").inputs.required` return 4 entries or 9, right now.

**Nine.** Re-read 2026-08-23 through **two independent endpoints**, both returning byte-identical
structure including the full `input_details` block:

```
get_node("SyncLipSyncNode").inputs.required
  = ["VIDEO","AUDIO","INT","COMFY_DYNAMICCOMBO_V3","COMBO","COMBO","INT","INT","INT"]

search_nodes(q="SyncLipSyncNode", detail="full")   ->  identical
```

The agent's surface returns **four**, with **no `input_details` structure at all**. Both readings
are honest reports of different tool surfaces over the same live catalog.

**Our round-14 diagnosis was wrong.** We said its surface returned "a lean/collapsed view" that
omits conditional sub-fields — implying a fuller view existed behind the same tool. It reported
that four *is* its fullest view and that `input_details` is absent entirely. We had no evidence for
the collapse hypothesis beyond its convenience. Recorded as ours.

**Its possibility (2) — that our nine was itself a relay artifact — is ruled out by architecture,
not by assertion.** Our `get_node` results are direct MCP calls inside our own session; they never
pass through the Director's copy-paste channel, which is the only path that has ever flattened
anything in this thread. Two corroborating consistency checks:

- The `required` array is **types-only, no names**. Fabrication would have had to inflate 4 → 9
  *and* emit a nameless type list whose trailing `COMBO, COMBO, INT, INT, INT` match the five named
  fields' declared types in exact order.
- The tooltips form a **closed reference graph**: `speaker_selection` names `speaker_x`/`speaker_y`/
  `speaker_frame`; each of those three independently states *"Only used when speaker_selection is
  'coordinates'."* `sync_mode`'s five values carry mutually consistent, non-obvious length
  semantics.

### Trap earned (the sharpest since round 11, and it is the agent's)

> **A node's schema can differ between two tool surfaces reading the same live catalog. A field
> absent from one surface may be present on another. Before concluding a node lacks an input, read
> it from a second independent surface.**

This sits one layer *earlier* than our standing "advertised is not runtime" rule. In the agent's
own words: **advertised differs between surfaces before runtime even enters.** Round 11 taught us
advertised ≠ runtime; round 14 teaches advertised ≠ advertised.

## 2. The near-miss it prevented — a green run with wrong content

Its stated consequence of building blind: *"a node that runs with default speaker behavior and
silently ignores every coordinate you send."*

`speaker_selection` defaults to `default` ("let the model decide"). A blind build would have
selected a face on its own, mouthed MAC's line on whichever man it picked, returned a valid MP4,
and **passed every container check we own**. No error, no failed validation — a completed, green,
plausible run whose content is wrong.

That is the fx-dub thesis exactly, and it would have landed in the visual domain where we have no
receipt yet. **The stop was worth more than the audition**, as round 14 §6 predicted it might be.

## 3. Consequence for the build

The agent is **out of the build path for `SyncLipSyncNode`** — it cannot address inputs its tool
does not expose, and asking it to guess dotted names it cannot see would manufacture exactly the
round-11 failure. We author and submit that graph from our side, where the five conditional fields
are addressable. The `fx-dub v3-sync` tab instruction from round 14 is **withdrawn**.

The frame extract (`LoadVideo` → `GetVideoComponents` → `ImageFromBatch` → `SaveImage`) uses no
dynamic combos and remains within its surface; offered as optional, explicitly skippable.

**Standing report accepted:** nothing built, no canvas touched, one read-only schema call; `v2.1`,
`v2.2`, both turbo tabs and its current focus all intact.

## 4. Open question handed back

Whether `input_details` is absent from **every** node on its surface or only from
`COMFY_DYNAMICCOMBO_V3` nodes. That distinction decides whether this is a general property of its
tooling or specific to dynamic combos, and it determines how much of this thread's schema record
needs re-reading from a second surface.

## 5. Still unproven

- Runtime acceptance of the dotted `model.*` slot names — now only settleable by our own submitted
  job, since the agent cannot express them.
- `SyncLipSyncNode.video` resolving a storage key with no upload.
- `sync_mode: silence` behaviour, and whether the pass re-encodes the audio track.
- Lip-sync quality at 16 fps against the node's 24/25/30 advisory, on profile faces at 480p.
