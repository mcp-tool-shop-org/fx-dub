# as-built — the Comfy Agent's v1 graphs (provenance archive)

These three graphs were built by the **Comfy Cloud in-app agent** during the Director-run dialog of 2026-08-21 and pulled over the API the same day (`get_saved_workflow`; canvas tabs are API-visible). They are archived **verbatim, defects and all** — they are the provenance baseline the v2 build order corrects, not the recommended graphs.

| File | Cloud record | Nodes | What it is |
|---|---|---|---|
| `describe-a-video-florence2.json` | tab "Describe a video (Florence2)" (file-based) | 13 | Full chain: video → Florence-2 caption → ACE-Step SFX + ChatterBox TTS → mean-mix → save |
| `demo-sfx-ace-step.json` | `0a8b29f6-c16c-4cd4-91ce-69d12bba1cc8` | 7 | Standalone SFX demo (rain ambience, hand-typed tags) |
| `demo-dialogue-chatterbox.json` | `843f8a61-e3a4-412e-b349-333fa827f290` | 2 | Standalone dialogue demo (default voice) |

**Demo runs verified from our side (2026-08-21):** billing feed shows exactly two jobs in the demo window — SFX `d3cda2f7-bc64-413e-ae14-dc0d279e5dff` (7.63 gpu-sec ≈ 2.0 cr) and dialogue `19c22524-a7b0-48ee-bb99-37e1651e8067` (6.54 gpu-sec ≈ 1.7 cr), both `rtx_pro_6000`. Outputs downloaded and header-decoded: SFX = 44.1 kHz stereo 16-bit 9.938 s (`sha256 676bbbcb…`), dialogue = **24 kHz mono** 16-bit 5.800 s (`sha256 7cf405e3…`). The dialogue run is the first end-to-end cloud measurement of `FL_ChatterboxTTS` (previously agent-reported only).

## Defect ledger (why v2 exists)

1. **ACE-Step 1.0, not 1.5** — `ace_step_v1_3.5b.safetensors` + `TextEncodeAceStepAudio` + `EmptyAceStepLatentAudio` (1.0 latent). The measured production lane is ACE-Step **1.5** (`acestep_v1.5_xl_base_bf16` + `ace_1.5_vae` + dual Qwen encoders, `TextEncodeAceStepAudio1.5`, euler/simple/50/cfg 6 + `ModelSamplingAuraFlow` shift 3, 48 kHz decode) — and 1.5 is **MIT code+weights** where 1.0 is Apache-2.0. The agent's "Apache" license claim was correct for the model it picked, and the better model has the better license.
2. **`microsoft/Florence-2-base` with `do_sample: true`** — non-deterministic captions break pinned-seed replay (and memo-cache pricing). The measured captioner (wave 8, `caption-florence2-v1`) pins `Florence-2-large`, fp16/sdpa, `do_sample=false`, fixed seed.
3. **Deprecated saver** — `SaveAudio` node titled "Save Audio (FLAC) (DEPRECATED)". House rule: masters via `SaveAudioAdvanced` (FLAC/WAV).
4. **No duration coupling** — bed hard-pinned to 10 s; `VHS_LoadVideo.video_info` (fps/duration) dangles unused. The bed must derive its length from the clip.
5. **Mixed-rate, mixed-channel mix** — `AudioCombine(method=mean)` sums ACE @ **44.1 kHz stereo** with ChatterBox @ **24 kHz mono** (both measured from the demo FLACs) with no resample, no upmix, no level control, no loudness target.
6. **No loudness manifest** — no `AudioLoudnessMeter` → `SaveText` (house convention: meter-to-file ships by default).
7. **Caption never reaches the output manifest** — the Florence `caption` STRING feeds the SFX tags but has no `SaveText`; run headlessly, the semantic intermediate is lost (trap-ledger rule: STRING outputs need SaveText).
8. **Frame-cap cost trap** — `frame_load_cap: 0` + `select_every_nth: 1` sends *every* frame of the clip to Florence-2 as a batch; a 60 s clip ≈ 1,700+ frames of captioning GPU-time. v2 samples sparsely (cap ≈ 8 frames, spread).
9. **Raw caption wired directly into SFX tags** — the research-grounded design (dispatch, choices A/D) inserts a deterministic caption→audio-prompt rewrite; a visual caption passed straight through measurably degrades T2A output (Sound-VECaps finding).
10. **No mux-back** — the pipeline ends at a FLAC; the actual dub deliverable is the video with its new soundtrack (`VHS_VideoCombine`), plus stems.

The v2 build order correcting all ten items is `docs/briefs/2026-08-21-fxdub-02-brief.md` (relayed to the Comfy Agent by the Director).

---

# as-built v2 — "fx-dub v2" (2026-08-21, round 2)

Archived: [`fx-dub-v2.api.json`](fx-dub-v2.api.json) (API form; the editor form lives in the cloud tab "fx-dub v2" and will be archived at v2.1 once the blockers below clear). 29 nodes, validates green, **runs never ordered**.

**Delivered as briefed (verified in the pulled JSON):** Florence-2-large fp16/sdpa `do_sample=false` seed 1 · caption → SaveText `fxdub/caption` · `TextEncodeAceStepAudio1.5` with tags from an editable primitive (caption NOT hard-wired) · shared PrimitiveInt seed → encoder + sampler · `ModelSamplingAuraFlow` shift 3 · Chatterbox default voice, script primitive, seed 42 · AudioStandardize(stereo) ×2 · AudioMix with primitive gains (VO 0 dB, bed −15 dB) · AudioLoudnessMeter ×2 → SaveText (`lufs_mix`, `lufs_vo`) · SaveAudioAdvanced FLAC ×3 (mix + stems saved PRE-gain, correct stem practice) · VHS_VideoCombine h264-mp4 with `frame_rate` wired from `VHS_VideoInfo.source_fps`.

**Defect ledger v2 (round-3 brief items):**

1. **F1 — KSampler `negative` is the same conditioning output as `positive`** (the v1 negative encoder was dropped). At cfg 6 the CFG algebra cancels — guidance silently off. Agent did not report this.
2. **F2 — the "ACE 1.5 XL files aren't installed" substitution claim is REFUTED.** Verified over the API: `UNETLoader` lists `acestep_v1.5_xl_base_bf16` (+ xl_sft/xl_turbo/turbo/base), `VAELoader` lists `ace_1.5_vae`, `CLIPLoader` lists all three `qwen_*_ace15` encoders with an `ace` type. The agent searched only `CheckpointLoaderSimple` (where only `ace_step_1.5_turbo_aio` lives). **Trap for the ledger: a checkpoint loader's COMBO is not the catalog — split-file diffusion models live under UNETLoader/VAELoader/CLIPLoader.** Bonus defect: the turbo AIO shipped with the XL-base recipe (50 steps / cfg 6) — turbo templates run ~8 steps / cfg 1.
3. **F3 — `skip_first_frames: 8` on the loader clips the first 8 frames from the DUBBED VIDEO** (same IMAGE stream feeds the mux), while `frame_load_cap: 0` still sends every frame to Florence (the cost trap, unfixed — capping at the loader would break the mux; needs a subsampler on the Florence branch only).
4. **F4 — `timesignature: "2"`** left at the 2/4 default.
5. **F5 — bed duration is a manual knob (10 s)**; `VHS_VideoInfo.source_duration` dangles unwired.

**Accepted honest platform answers (agent-reported, recorded):** no sample-rate-conversion node on the allowlist (AudioStandardize conforms channels only; AudioMix's rate reconciliation is undocumented — we measure the mix header at audition) · no shot-boundary or onset node (spot-effect timing goes host-side; `AudioPad`+`AudioMix` is the placement pair) · `AudioCombine` methods add/mean/subtract/multiply/divide, no gain input · Qwen3-TTS = `FB_Qwen3TTS*` node family, output rate undocumented.

The v2.1 fix order is `docs/briefs/2026-08-21-fxdub-03-brief.md`.
