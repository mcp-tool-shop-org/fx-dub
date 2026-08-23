# fx-dub round 13 — verification (ours)

Paired with the agent's round-13 reply (relayed 2026-08-23; archived as
[`2026-08-23-fxdub-13-reply.md`](2026-08-23-fxdub-13-reply.md)). Outbound response: round 14.

**Round scoreboard: our defects 2, the agent's 1.** First round in four where its count is not zero
— and it invited the check itself (*"this is the thing in section 4 I think may be wrong, and you
asked me to say so before a paid run"*), which is the behaviour we want regardless of the outcome.

## 1. REFUTED — `SyncLipSyncNode` does expose the coordinate inputs (Class A)

**Agent's claim:** the live node shows only `video`, `audio`, `seed`, `model`; *"no sync_mode, no
speaker_*, no speaker_x/y at the top level… the whole frame-extract → speaker_x/speaker_y plan may
target inputs that don't exist on this node."*

**Refuted by `get_node("SyncLipSyncNode")`, pulled 2026-08-23.** Two independent proofs in one
response:

1. **The required-type array has nine entries**, before any name is read:
   `["VIDEO","AUDIO","INT","COMFY_DYNAMICCOMBO_V3","COMBO","COMBO","INT","INT","INT"]`.
   The agent's four account for the first four. The trailing `COMBO, COMBO, INT, INT, INT` are
   `sync_mode`, `speaker_selection`, `speaker_frame`, `speaker_x`, `speaker_y`.
2. **`input_details` carries all five**, each `"conditional": true, "applies_when": ["sync-3"]`,
   with full tooltips — including `speaker_selection`'s *"coordinates: target the face at pixel
   (speaker_x, speaker_y) in the frame chosen by speaker_frame."*

The `model` field's `hint` states the dotted-name mechanism verbatim. **`sync-3` is the only option
`model` accepts**, so the conditionals do not merely exist — they always apply.

**Diagnosis:** the agent's surface returned a *lean/collapsed* view that omits conditional
sub-fields; ours returned the expanded one. Its inference ("nested behind the dynamic combo") was
correct; the conclusion it drew ("as read cold, exposes no coordinate inputs") was not. Its
recommended option (b) — hold — was void, though its option (a) was right for other reasons.

**Trap earned:** *the same node reads differently through a lean view and an expanded view; a
missing conditional sub-field is evidence about the view, not about the node.* Sibling of round
10's *"the editor graph and the node schema are different views."*

## 2. Blocker 1 dissolved locally — the ask was malformed, and unnecessary

**Agent is right:** `get_output` takes a `prompt_id`; handed a storage hash it returns HTTP 400.
Round 13 §5 told it to "call `get_output` on both MAC keys." **That is our defect** — a type
mismatch, not a refusal, and it names an addressing distinction we already carry (trap 27: the
storage key and the content sha256 are two addresses for one file; neither is a job id).

**The probe was never needed.** Measured locally, no credits:

| Artifact | Measured |
|---|---|
| `runs/2026-08-22-fxvox7-two-voice/mac_onframe_pitch0.flac` | **4.032 s**, 48 kHz, stereo |
| MAC isolated content (`mac_original_isolated.flac`) | 1.72 s |
| MAC's window in the shipped scene (word timings) | 2.279 s → 3.959 s |

`4.032 − 1.72 = 2.312 s` leading material vs a **2.279 s** measured onset. **Trap 58 confirmed:
ByteDance's absolute output timeline writes the leading silence into the file, so MAC's render is
already a correctly positioned stem.** No `EmptyAudio`/`AudioConcat` assembly is required, and the
`AudioPad`-is-broken fallback never comes into play.

Consequence for round 14: use `d7ba748c…` directly; its exact length is immaterial because
`sync_mode: silence` pads the shorter track to the 10.0625 s picture.

**Gap noted:** the KB `runs` table holds no `job_id` for the ByteDance MAC/VOICE renders or the v28
delivery run. That is why no prompt_id could be handed over. → open action.

## 3. Kling — the agent's correction is right and upgrades our record

**Agent's claim:** the node exposes no height/width/length widgets, so the 720–1920 px / 2–10 s
bounds cannot be confirmed "from the live schema."

**Upheld.** Our numbers came from the node's **description string**, not from numeric widget
bounds — round 13 §5 item 4 asked it to confirm from the schema what lives in prose. Half ours.

**Its consequence is the material finding:** those limits are enforced **server-side at run**, so a
violating graph validates clean and fails after credits are committed.

**Trap earned:** *a partner node's operating constraints can live only in its description text,
where the validator cannot see them.* Sibling of "a `dry_run` PASS is not proof." The Kling
disqualification stands on the underlying API limits (our clip is 832 × 480 and 10.0625 s); we will
not claim the node advertises them.

## 4. Confirmations received

- `LoadVideo` live: single `file` input with an empty/unlisted options set that still resolves an
  arbitrary key — **matches trap 26**, round 9. Cleared for the extract.
- `GetVideoComponents` outputs `images, audio, fps, bit_depth`; index 0 is `images` — our graph's
  `["2", 0]` is correct. `ImageFromBatch` takes `image, batch_index, length`. Four-node decode
  graph confirmed sound by both sides.

## 5. The flattening artifact recurred again — 6th and 7th occurrences

This reply carried `` `` `` placeholders at *"``/get_job take a run's prompt_id"*, *"the correct
read … is ``"*, *"voice_language —, choices"*, and `LoadVideo`'s type rendered as `****`. Consistent
with rounds 8, 10, 12-inbound and 12-reply. No action beyond the standing rule: **names never cross
this channel authoritatively; re-derive at point of use.**

## 6. Still unproven

- Runtime acceptance of the dotted `model.*` slot names (advertised ≠ runtime; round 11 precedent).
- `SyncLipSyncNode.video` resolving a storage key with no upload — the extract run answers the
  `LoadVideo` half only.
- `sync_mode: silence` behaviour, and whether the pass re-encodes the audio track.
- Lip-sync quality at 16 fps against the node's 24/25/30 advisory, on profile faces at 480p.
