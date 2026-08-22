# fx-dub round 9 — verification (advisor side, measured)

**Pulled 2026-08-22T00:26Z** via `get_saved_workflow(filename="fx-dub v2.2.json")`.
Every claim below is class **A** (measured from the pulled JSON / `get_node`), not relayed.

## Timeline (correlated, UTC)

| When | What | Source |
|---|---|---|
| 00:14:29Z | round-9 brief written | local mtime |
| 00:22:23Z | `fx-dub v2.2` tab created — **0 nodes, 239 bytes** | `list_saved_workflows` |
| ~00:26Z | `fx-dub v2.2` complete — **34 nodes** | `get_saved_workflow` |

The brief **was** relayed. The empty tab was a build in progress, not a stall.

## PASS — the ingest rewiring is correct

Traced from the `links` array, not from node presence:

| # | Claim | Evidence |
|---|---|---|
| 1 | `LoadVideo.VIDEO` → `GetVideoComponents.video` | link `289825242746571` |
| 2 | `GetVideoComponents.IMAGE` → `VHS_SelectEveryNthImage` | link `4353181531463535` |
| 3 | `GetVideoComponents.IMAGE` → `VHS_VideoCombine.images` | link `3764324982370696` |
| 4 | `VHS_VideoInfo` removed | absent from node list |
| 5 | `VHS_LoadVideo` removed | absent from node list |
| 6 | `GetVideoComponents` AUDIO output unconnected | `links: []` (correct — source is silent) |
| 7 | `GetVideoComponents` fps FLOAT unconnected | `links: []` (as ordered — measure at audition) |

## PASS — the deferred frame_rate verification is CLOSED

The handoff carried this as still-open ("node presence verified; the link is not"). It is now measured:

- link `718920623009028`: `PrimitiveFloat(520870296421658) → VHS_VideoCombine` **input index 4 = `frame_rate`**
- `VHS_VideoCombine.inputs[4].link = 718920623009028` (the input is genuinely connected)
- `api_format` resolves it: `"frame_rate": ["520870296421658", 0]` — the link, not a literal
- `PrimitiveFloat(520870296421658).value = 16`

⚠ **Latent trap recorded:** the widget *underneath* that link still reads `frame_rate: 8`.
The link wins while it exists. If it is ever cut, the mux silently falls back to **8 fps** —
161 frames would render as a 20.1 s video against a 10 s bed, and nothing would error.
The same stale-widget-under-live-link pattern is present and harmless on
`TextEncodeAceStepAudio1.5` (duration 120), `EmptyAceStep1.5LatentAudio` (seconds 120),
`KSampler` (seed 0), and `FL_ChatterboxTTS` (text "Hello, this is a test.") — all
verified resolving to their links in `api_format`.

## PASS — drift fixed, artifacts namespaced

- Florence task is now **`more_detailed_caption`** (v2.1 carried the `detailed_caption` drift). `do_sample=false`, `num_beams=3`, `seed=1`.
- All seven `filename_prefix` values are under `fxdub22/`: `caption`, `mix_lufs`, `vo_lufs`, `mix`, `stem_bed`, `stem_vo`, `dubbed`.
- Mix bus intact: VO → `AudioStandardize`(stereo) → `AudioMix.audio_1` @ gain **0 dB**; bed → `AudioStandardize`(stereo) → `AudioMix.audio_2` @ gain **−15 dB**. Meters on the mix and on the VO stem. `ConditioningZeroOut` on the negative. Shared `PrimitiveInt(1)` → both `TextEncodeAceStepAudio1.5.seed` and `KSampler.seed`. Duration `PrimitiveFloat(10)` → both the encoder and the latent.
- `fx-dub v2.1` untouched (32,344 B, mtime 2026-08-21T23:12:00Z — predates the v2.2 tab).
- No fx-dub job in `get_billing_activity`. The validate-only rule held.

## ✅ RESOLVED — the loader value is correct (my "blocker" was wrong)

**I called this a hard blocker. It was not. Correcting the record.**

`LoadVideo.file` is set to
`ea68c5aada3b35b0c8be343f52671cf40ef30066b7d2852766ffe86f1292e5c9.mp4`, which does **not**
appear in the `LoadVideo.file` COMBO that `get_node` enumerates (nine entries, eight unique,
pulled twice, byte-identical). I read that absence as "invalid COMBO value → the audition
fails validation at the loader."

That inference was wrong, and it is *the trap ledger firing on me*: **"two probes reading
different fields aren't a contradiction"** and **"a loader's COMBO is not the catalog."** The
agent's counter-evidence — the platform's own validator returning `ready_to_run: true,
error_count: 0` — was the more authoritative probe of the same question.

`estimate_credits` could not adjudicate: a minimal `LoadVideo → GetVideoComponents → SaveImage`
graph priced identically (0 credits, no error) whether given the agent's value or a known-good
COMBO entry as a control. It is a pricing pass, not a validator.

**`get_output` settled it.** Against the Wan job that produced the fixture
(`1c4e02a8-0a7f-4806-b548-201160f42530`):

```
class_type       : SaveVideo
filename_prefix  : video/ComfyUI
filename         : ea68c5aada3b35b0c8be343f52671cf40ef30066b7d2852766ffe86f1292e5c9.mp4
content-disposition: attachment; filename="video/ComfyUI_00001_.mp4"
```

So `ea68c5aa…` is the real storage key of our clip, and `video/ComfyUI_00001_.mp4` is its
display name — exactly as the agent reported, both of them.

### The agent's declared gap is now closed — by our own probe, on the actual bytes

The agent flagged that the per-stream detail (frames / fps / codec) was truncated before it
could read it, and offered to find another read path. It does not need one. We downloaded the
asset and ran `tools/media_probe.py` on it:

| measured on `ea68c5aa…mp4` (downloaded) | value |
|---|---|
| sha256 of the served bytes | `9985a8ba6197ea7c02adc99c4c3aafc2a9d1cfa13e535ede64908ebea327a30c` |
| bytes | 963,326 — **byte-identical to the local fixture** (`b == local` → `True`) |
| frames | **161** |
| duration | **10.0625 s** (track timescale 16384 = `time_base 1/16384`) |
| tracks | one video, **no audio** |
| implied fps | 161 / 10.0625 = **16.000** — the `PrimitiveFloat` pin is exactly right |

**The full five-point signature is confirmed.** The agent's identification was correct on
every axis, including the two it honestly declined to claim.

### The reconciliation — and the new trap

`ea68c5aa…` is the **cloud storage key** (Comfy's content address in `comfy-cloud-assets`).
`9985a8ba…` is the **sha256 of the same bytes**. Two addresses for one file. That is why the
earlier session correctly observed "the cloud's content addresses are not sha256 of the served
bytes" — and then wrongly concluded local matching was impossible. It is possible; you just
have to map job → asset key with `get_output` first, then download and hash.

**New trap earned:** `get_node("LoadVideo").file` enumerates the *input/attachment* namespace.
A cloud `SaveVideo` output lives in the asset store under a storage key that `LoadVideo` will
also resolve but which that COMBO does not list. **Absence from the COMBO is not proof of
invalidity.** The authoritative job→asset mapping is `get_output(prompt_id)`.

### Consequence for the marked-copy plan

`~/Downloads/fxdub-audition-clip-MARKED.mp4` (frame-identical, sha256 `68763fc6…`) was built as
a set-difference identification path. **It is not needed — do not attach it.** Keeping it on
disk as a standing fallback for the day we must identify a genuinely ambiguous attachment.

## Secondary findings (round-10 cleanup, neither blocks the audition)

1. **`Florence2Run.control_after_generate = "randomize"`** — every other seeded node in the
   graph is `"fixed"` (`KSampler`, `TextEncodeAceStepAudio1.5`, `PrimitiveInt`). The value
   submitted for this run is `seed: 1` (verified in `api_format`), so the audition is
   unaffected, but the canvas seed mutates after each run and byte-identical replay from the
   tab breaks. Violates PIN_PER_STEP. Set it to `fixed`.
2. **`FL_ChatterboxTTS.seed = 0`, not linked to the shared `PrimitiveInt(1)`.** Class **B —
   advisory.** The node spec gives `seed` as `INT, default 0, min 0` — `0` is inside the
   legal range, so it is most likely a literal seed rather than a randomize sentinel, and the
   VO is probably replayable as-is. We have not measured this. Either link it to the shared
   seed primitive or confirm determinism with a repeat run before treating the VO stem as
   replayable in any A/B.

## Also measured

- **`fx-dub v2.1-turbo` does not exist.** The full workspace listing was walked (105
  workflows, 3 pages). Round 8's controlled A/B was never built. Not a blocker — it is a
  post-audition comparison — but the round-8 order is outstanding and should not be assumed done.
- `GetVideoComponents` confirmed real: `pack: core`, `category: video`, `VIDEO → IMAGE, AUDIO,
  FLOAT, INT`. The round-9 architecture was sound.
