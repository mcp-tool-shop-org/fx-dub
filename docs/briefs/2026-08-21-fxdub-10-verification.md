# fx-dub round 10 — verification (advisor side, measured)

**Pulled 2026-08-22** via `get_saved_workflow(filename="fx-dub v2.1-turbo.json")`, full graph,
diffed value-by-value against the `fx-dub v2.2` pull in the same session. Class **A**.

## PASS — the turbo A/B is textbook

34 nodes (same as v2.2). `CheckpointLoaderSimple` is gone; the split stack is back.
**Exactly three values differ from v2.2**, which is what makes this a controlled experiment:

| Node | Value | v2.2 | v2.1-turbo |
|---|---|---|---|
| `UNETLoader` | `unet_name` | `acestep_v1.5_xl_base_bf16.safetensors` | **`acestep_v1.5_xl_turbo_bf16.safetensors`** |
| `KSampler` | `steps` | 50 | **8** |
| `KSampler` | `cfg` | 6 | **1** |

All three match the official `audio_ace_step1_5_xl_turbo` template exactly.

### Held constant — every value checked, not sampled

- `UNETLoader.weight_dtype` `default` · `VAELoader` `ace_1.5_vae.safetensors` ·
  `DualCLIPLoader` `qwen_0.6b_ace15` + `qwen_4b_ace15`, type `ace`, device `default`
- `ModelSamplingAuraFlow.shift` **3** · `KSampler` `euler` / `simple` / `denoise 1`
- `TextEncodeAceStepAudio1.5`: **`cfg_scale` 2**, bpm 120, timesignature `"4"`, language `en`,
  keyscale `C major`, `generate_audio_codes` true, temperature 0.85, top_p 0.9, top_k 0, min_p 0
- Florence block: `Florence-2-large` / fp16 / sdpa / `more_detailed_caption` / `do_sample=false`
  / `num_beams=3` / `seed=1` · `VHS_SelectEveryNthImage(30)`, `skip_first_images=0`
- `FL_ChatterboxTTS`: exaggeration 0.5, cfg_weight 0.5, temperature 0.8, seed 0 (identical —
  including the open seed-0 question)
- Mix bus: `AudioStandardize`×2 stereo → `AudioMix` (VO `audio_1` @ gain 0 dB, bed `audio_2` @
  gain −15 dB) → meters on the mix and on the VO stem
- `VHS_VideoCombine`: h264-mp4, `pix_fmt` yuv420p, `crf` 19, `save_metadata` true,
  `trim_to_audio` false, `loop_count` 0, `save_output` true
- Shared `PrimitiveInt(1)` → `TextEncodeAceStepAudio1.5.seed` (link `1289806432723668`) **and**
  `KSampler.seed` (link `2282223038865124`) · duration `PrimitiveFloat(10)` → encoder **and** latent
- Ingest: `LoadVideo(ea68c5aa…mp4)` → `GetVideoComponents` → IMAGE to **both**
  `VHS_SelectEveryNthImage` (link `4018831087736651`) and `VHS_VideoCombine.images` (link
  `3285138440472038`); AUDIO and fps outputs unconnected
- `PrimitiveFloat(16)` → `VHS_VideoCombine.frame_rate` on input slot 4 (link `2702567314221210`)
- **Same clip** in both tabs — essential; an A/B on different footage would be worthless
- All seven prefixes under `fxdubturbo/` (caption, mix_lufs, vo_lufs, mix, stem_bed, stem_vo, dubbed)

⚠ Carried forward from v2.2: the `frame_rate` widget beneath the live link still reads `8`.
Harmless while linked, silent 20.1 s dub if ever cut.

## The agent was right again, and our round-10 ask was the flawed one

**`Florence2Run.control_after_generate` cannot be set through the API, and the agent said so
rather than faking a fix.** Confirmed from our own pull: that node's `inputs` array carries
`seed` (INT, `widget: {name: "seed"}`) and **no `control_after_generate` entry at all**. The
value shows up in `widgets_values` (positional, 10th) and in `widgets_values_named`, but there
is no input to address, so there is nothing for an API caller to set.

This is the same shape as the loader mistake earlier in this session: the editor JSON and the
node schema are *different views*, and a value present in one is not necessarily settable
through the other. Our instruction was not actionable; the agent's refusal to invent a target
was correct.

**Practical impact: none.** `api_format` submits `seed: 1`, and `do_sample=false` means the
caption is decoded greedily/beam — the seed barely participates. The only cost is canvas drift
after a run, fixable in the browser if it ever matters. **Dropping this item.**

**`FL_ChatterboxTTS` seed-0 semantics: "cannot determine."** Exactly the answer requested. The
node spec exposes `seed` as a required INT (`default 0, min 0`) with no documented sentinel, so
neither side can settle it from the schema. It stays open, to be settled by a repeat run after
the audition — recorded as class **B**, advisory, and the VO stem must not be treated as
replayable until then.

**Rename:** the agent has no rename tool. `fx-dub v2.1-turbo` keeps a name that misstates its
lineage (it is built on v2.2's ingest). Cosmetic; rename in the browser or leave it and rely on
this record.

## Note on the reply channel

Both agent replies this round arrived with **tab names and node references flattened to the
literal strings "node" and "fx-dub the model"** ("node is gone", "node.unet_name = …", "rename
this tab to fx-dub the model"). The same garbling hit the round-8 reply. It did not cost us
anything — every claim was verifiable from the pulled JSON — but it is a second channel defect
after the round-8 truncation. **Do not resolve a garbled reference by inference; pull and look.**

## Both graphs are cleared to run

`fx-dub v2.2` (base, 50 steps / cfg 6) and `fx-dub v2.1-turbo` (turbo, 8 steps / cfg 1) are
built, verified, and pointed at the same clip with the same seed and the same mix bus. Nothing
blocks the audition but the Director's order.
