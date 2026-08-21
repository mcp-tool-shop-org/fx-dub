# fx-dub Knowledge Base — your options at every stage

The pipeline: **video → describe → (rewrite) → generate SFX/ambience + dialogue → mix → re-mux**.
Every stage has local and cloud options, and permissive and paid options. **License is the decisive axis** — a wrapper node's license is *not* the model weights' license, and only the weights license decides whether you can ship what you generate. Rows below are labeled:

- ✅ **publishable** — permissive on code AND weights (MIT/Apache-class); safe for a commercial release
- ⚠ **conditional** — commercial use allowed with conditions (revenue caps, extra terms riders)
- ⛔ **not for commercial work** — research/NC weights or proprietary API output terms you must read
- 💰 **paid API** — proprietary partner endpoint; quality is often excellent, licensing is their ToS, not yours

Facts marked *(measured)* were verified on-account (billing feed, pulled graphs, decoded output headers) in the readouts model-knowledge KB, waves 7–8 and this repo's receipts. Facts marked *(agent-reported)* come from the Comfy Cloud in-app agent's live-catalog view and are advisory until measured.

## Stage 1 — describe the video

| Option | Where | License | Notes |
|---|---|---|---|
| **Florence-2-large** (`Florence2Run`) | local + cloud | ✅ MIT | The default. Captions **sampled frames (stills), not motion** — cap the frame count (≈8, spread across the clip); `do_sample=false` + fixed seed for reproducible captions. Cloud cost *(measured)*: **6.73 gpu-sec ≈ 1.8 cr per caption**. Local native-transformers loading needs the `florence-community/Florence-2-large` conversion (the `microsoft/*` originals require `trust_remote_code`); ComfyUI's wrapper node handles this internally. |
| Qwen2.5-VL-class video-LLM | local | ✅ Apache-2.0 (7B) | Motion-aware, second-level event localization *(model-card claim)*. Heavier; advisory tier — no published head-to-head shows motion-aware captions improve downstream **audio** (dispatch finding 18). |
| GPT-4o / Gemini vision | cloud | 💰 | Best prose; API ToS; not for the publishable lane. |

**Honest limit:** captions are a *semantic* channel, not a temporal one. Text tells the generator *what* the scene sounds like, never *when* things happen (dispatch findings 1–3). fx-dub v1 is ambience/dialogue-grade; impact-synced foley needs an event timeline (roadmap) or a direct video→audio model (below).

## Stage 1.5 — caption → audio prompt (the rewrite)

A visual caption fed straight into an audio model **degrades** output — visual-only detail ("a blue bedspread, a framed poster") is noise to a T2A model (finding 11). The rewrite stage:

1. **strips non-audible detail** (subtractive first),
2. names **sound source + action + room/production character** in prose (Stable Audio's own schema; prose beats bare tags),
3. runs **deterministically** (temperature 0, pinned model + prompt, output cached in the manifest) — near-synonym prompt drift measurably shifts acoustics.

Local default: a small LLM via Ollama. Cloud: edit the prompt text box by hand (a human is a fine rewriter). For ACE-Step music beds, use the measured grammar: `Genre:`-prefixed concrete **musical prose** — comma-tag soup is rhythm-unstable and narrative lore-prose is deprecated *(measured, readouts prompt lab)*.

## Stage 2a — SFX / ambience bed

| Option | Where | License | Notes |
|---|---|---|---|
| **ACE-Step 1.5** (`TextEncodeAceStepAudio1.5`) | local + cloud | ✅ **MIT code+weights** | The publishable default for beds and music. Measured recipe: euler/simple/50 steps/cfg 6/`ModelSamplingAuraFlow` shift 3; 48 kHz decode; authored bpm/keyscale (34-value COMBO — modal color goes in the tags); **production window 60 s** (melody collapses past ~a minute); slow cues (≤70 bpm) lose ~1 take in 5 to loudness collapse — plan extra takes, not better adjectives *(all measured)*. ~8 cr per unit class on cloud. |
| ACE-Step 1.0 (`TextEncodeAceStepAudio`) | local + cloud | ✅ Apache-2.0 | What the in-app agent built first. Works (44.1 kHz decode); superseded by 1.5 on both quality and license. 10 s @ 50 steps ≈ 7.6 gpu-sec ≈ 2.0 cr *(measured)*. |
| **Stable Audio 3 Medium / Small-SFX** | local + cloud (Medium) | ⚠ Stability Community License **+ Gemma-ToU rider** | The SFX specialist. Free commercial **only under $1M/yr revenue**; the T5Gemma text encoder adds a Gemma terms rider — both verified. Cloud recipe *(measured)*: flat graph, lcm/8 steps/cfg 1, 44.1 kHz, ~2.6 cr/10 s; durations snap to the 2^n latent grid (read actual file duration); **no inpaint/continuation on cloud** — loop seams via concat/fades or local. Not "permissive" — the in-app agent's first description of it was wrong, ours was verified against the license text. |
| AudioGen / AudioLDM2 | local | ⛔ CC-BY-NC | Research only. |
| ElevenLabs SFX (`ElevenLabsTextToSoundEffects`) | cloud | 💰 | Excellent dedicated SFX; ≤30 s/generation, single flat clip, no stems. |
| ByteDance Seed Audio / Sonilo | cloud | 💰 | Partner APIs; Sonilo VideoToMusic takes video directly (skips the describe step). |

## Stage 2b — direct video→audio (the sync-first alternative)

These models watch the video and generate synchronized foley — structurally better timing than any caption path (~80–110 ms offsets). **Every open-weight one is commercially blocked** (verified):

| Model | License reality | Verdict |
|---|---|---|
| MMAudio | code MIT, **weights CC-BY-NC 4.0** | local experiments only, ⛔ for shipping |
| ThinkSound | Apache-2.0 code but **research/education only**; bundled Stability VAE needs separate permission | ⛔ |
| HunyuanVideo-Foley | Tencent Hunyuan Community License | ⚠ read the terms; regional/scale conditions |
| Woosh (Sony) | code MIT, **open weights non-commercial** | ⛔ |

If your project is non-commercial, MMAudio via `kijai/ComfyUI-MMAudio` is the strongest local sync path. fx-dub's caption-mediated lane exists precisely because the license wall makes text-conditioned models (ACE, SA3, Chatterbox) the only shippable ones.

## Stage 3 — dialogue / VO

| Option | Where | License | Notes |
|---|---|---|---|
| **Chatterbox** (`FL_ChatterboxTTS`, Resemble AI) | local + cloud | ✅ MIT | The publishable default. `audio_prompt` is OPTIONAL → default voice runs headlessly on cloud *(measured this repo: 6.5 gpu-sec ≈ 1.7 cr for a 5.8 s line; output **24 kHz mono** — the mix bus must resample/upmix)*. Every output carries Resemble's **Perth** perceptual watermark — that is a feature; leave it on. **Voice cloning is local-only** (cloud has no audio-upload path) and MIT does not waive **consent** — clone only voices you have rights to. |
| Chatterbox DialogTTS (multi-speaker A–D) | local only | ✅ MIT | Requires reference-voice AUDIO inputs → no cloud path. |
| **Qwen3-TTS** (`FB_Qwen3TTS*`) | cloud + local | ✅ Apache-2.0 | The Apache cloud-VO pillar: preset speakers + text-designed voices *(agent-reported node set; run one line before relying)*. Clone-reference audio is still local-only. |
| Kokoro-82M | local | ✅ Apache-2.0 | Consent-free by construction (fixed preset voices, no cloning); CPU-capable. Not on the cloud allowlist *(verified absent)*. |
| VibeVoice | local | ⚠ MIT-historical | Microsoft pulled the original repo after misuse reports; survives as a community fork. Supply-chain/optics risk — not the default. |
| ElevenLabs / OpenAI TTS | cloud | 💰 | Best-in-class quality + voice library; their ToS. |

## Stage 4 — mix & master (evidence-based defaults)

- Resample every branch to **48 kHz** before the bus (measured branch rates: ACE 1.5 = 48 k, ACE 1.0 = 44.1 k, SA3 = 44.1 k, Chatterbox = 24 k mono).
- **Dialogue is the anchor element** (ATSC A/85). Bed sits **−15 LU under dialogue** for ambience, **−10 LU** for music (AES/JAES listening studies; biased toward the louder-dialogue preference of non-expert listeners). Expose the offset — preferences spread ~5.7 LU between people.
- Integrated target **−18 LUFS** (AES TD1008 "Assorted" = speech+music+effects), true peak ≤ **−1 dBTP**. Broadcast deliveries retarget to −23 (EBU R128) / −24 (ATSC); Netflix near-field spec is −27 dialog-gated, TP ≤ −2.
- The manifest reports: BS.1770 revision, integrated + dialogue-gated LUFS, max true peak, LRA, and speech-to-background difference per window (floor: 4 LU, DPP).
- Masters: `SaveAudioAdvanced` **FLAC** (never the deprecated `SaveAudio`/MP3 — MP3 padding breaks alignment).

## Stage 5 — deliverables ("the dub kit")

`dubbed.mp4` (audio muxed back onto the source clip — `VHS_VideoCombine`) · `mix.flac` (48 kHz master) · `stems/` (bed, dialogue, spots) · `caption.txt` + `audio_prompt.txt` · `manifest.json` (loudness report + provenance block: models, seeds, graph hash, watermark presence). Stems-not-just-mix is what the strongest commercial tool (ElevenLabs Dubbing Studio) ships and what the research says editors need.

## Cloud platform traps (measured, readouts trap ledger)

- **No audio upload path** on Comfy Cloud → any node needing reference AUDIO (cloning, multi-speaker dialog) is local-only; cloud reference voices must be generated in-graph.
- **Editor-valid ≠ API-valid**: COMBO values are type-strict at `/api/prompt` (`"4"` passes, `4` fails); UI-only nodes silently vanish headlessly — graphs must be static-validation green.
- Queue caps at **100 jobs account-wide** — serialize batch submission.
- Pinned-seed byte-identity is **memo-cache-only**; a fresh re-execution reproduces the sound, not the bytes. Treat downloaded masters as canonical-by-hash.
- Rejected jobs bill zero; memoized replays still bill load/verify overhead (~0.8–3.5 gpu-sec).

## Publishing & governance (read before you ship a dubbed video)

- **EU AI Act Art. 50** is in force (applies from 2026-08-02): synthetic audio must be machine-readably marked (fx-dub's manifest + the Perth watermark serve this), and **the publisher of a deepfake-class dub carries the disclosure duty** — clear and distinguishable, at first exposure; lighter for evidently artistic/fictional works.
- **YouTube** requires the synthetic-media disclosure toggle for realistic content — but exempts *cloning your own voice* for dubs. **TikTok auto-labels from C2PA** metadata.
- **US:** AI voices in robocalls are illegal without prior consent (FCC 24-17). Tennessee's ELVIS Act attaches liability to tools purpose-built to clone an identifiable person's voice — fx-dub stays general-purpose and ships no person-specific voice packs; you supply consent for any reference voice.
- **Watermarks are defeatable** (adaptive attacks reach 0% detection in the literature) — which is why fx-dub layers watermark + manifest + consent record instead of trusting any one mechanism. Don't strip Perth; it is your own Art. 50 compliance.
