#!/usr/bin/env python3
"""Build kb/fxdub.db — the fx-dub project knowledge database.

Idempotent: drops and recreates every table from the seed data below, which is
the single source of truth (edit THIS file, rerun, commit both). Every row
carries a class:
  A = measured/verified on-account (billing feed, API pull, decoded bytes, get_node)
  B = agent-reported or otherwise second-hand; advisory until measured
Dates are verification dates; the 30-day freshness rule applies (stale = advisory).

Run:  python kb/build_db.py        (from repo root; writes kb/fxdub.db)
Query examples: see kb/README.md
"""
import sqlite3, os, datetime

DB = os.path.join(os.path.dirname(__file__), "fxdub.db")

NODES = [
    # (name, pack, status, cls, notes)
    # status: present = verified in live catalog (get_node / pulled graph); reported = agent-reported; absent = verified/reported absent
    ("UNETLoader", "core", "present", "A", "COMBO carries acestep_v1.5_xl_base_bf16 + xl_sft + xl_turbo + 1.5_turbo + 1.5_base. Split-file diffusion models live HERE, never in CheckpointLoaderSimple."),
    ("VAELoader", "core", "present", "A", "COMBO carries ace_1.5_vae.safetensors."),
    ("CLIPLoader", "core", "present", "A", "COMBO carries qwen_0.6b/1.7b/4b_ace15; type COMBO includes 'ace'."),
    ("DualCLIPLoader", "core", "present", "A", "Used by the measured Motif reference stack to load both qwen ace15 encoders."),
    ("CheckpointLoaderSimple", "core", "present", "A", "Carries ace_step_1.5_turbo_aio.safetensors (AIO: MODEL+CLIP+VAE). Its list is NOT the catalog."),
    ("TextEncodeAceStepAudio1.5", "core", "present", "A", "tags/lyrics/seed/bpm/duration/timesignature(2,3,4,6 STRING)/language/keyscale(34 COMBO)/codes-LM knobs. Grammar: 'Genre:' concrete musical prose (measured, prompt lab)."),
    ("EmptyAceStep1.5LatentAudio", "core", "present", "A", "The 1.5 latent node (seconds 1-1000). v2 wrongly used the 1.0 node with the 1.5 stack."),
    ("EmptyAceStepLatentAudio", "core", "present", "A", "The 1.0 latent node ('Empty Ace Step 1.0 Latent Audio')."),
    ("ModelSamplingAuraFlow", "core", "present", "A", "shift 3 in the measured ACE recipe."),
    ("ConditioningZeroOut", "core", "present", "A", "The reference stack's negative-conditioning source."),
    ("KSampler", "core", "present", "A", "XL-base measured recipe: euler/simple/50 steps/cfg 6."),
    ("VAEDecodeAudio", "core", "present", "A", "ACE 1.0 decodes 44.1 kHz stereo (measured); ACE 1.5 mix decodes 48 kHz (KB wave 7)."),
    ("Florence2Run", "comfyui-florence2", "present", "A", "Pin do_sample=false + fixed seed for reproducibility. Cloud cost ~6.73 gpu-sec/caption (wave 8)."),
    ("DownloadAndLoadFlorence2Model", "comfyui-florence2", "present", "A", "microsoft/Florence-2-large fp16/sdpa is the measured captioner config."),
    ("FL_ChatterboxTTS", "FL pack", "present", "A", "audio_prompt OPTIONAL -> default voice runs headlessly. Output 24 kHz MONO (measured). Perth watermark embedded."),
    ("FL_ChatterboxDialogTTS", "FL pack", "reported", "B", "Multi-speaker A-D; REQUIRES speaker reference AUDIO -> local-only (no cloud audio upload)."),
    ("VHS_LoadVideo", "videohelpersuite", "present", "A", "skip_first_frames/frame_load_cap act on the ONE output stream — capping here starves the mux (trap 8)."),
    ("VHS_VideoInfo", "videohelpersuite", "present", "A", "Unpacks video_info -> source/loaded fps, frame_count, duration, w/h (10 outputs)."),
    ("VHS_VideoCombine", "videohelpersuite", "present", "A", "AUDIO input optional; formats gif/webp/h264-mp4/h265-mp4/ffmpeg-gif/webm; frame_rate FLOAT-wirable; trim_to_audio bool."),
    ("VHS_SelectEveryNthImage", "videohelpersuite", "present", "A", "images->IMAGE+count; select_every_nth + skip_first_images. The Florence-branch subsampler (F3 fix)."),
    ("AudioStandardize", "AudioTools", "present", "A", "Channel layout ONLY (mono/stereo). NOT a sample-rate converter."),
    ("AudioMix", "AudioTools", "present", "A", "Sum of two streams + per-input gain_db. Rate reconciliation policy undocumented — measure output header."),
    ("AudioCombine", "AudioTools", "present", "A", "method add/mean/subtract/multiply/divide; NO gain input; add is clip-prone."),
    ("AudioLoudnessMeter", "AudioTools", "present", "A", "loudness_info STRING ('Integrated Loudness: X LUFS') — needs SaveText to reach outputs."),
    ("SaveAudioAdvanced", "core", "present", "A", "The blessed master saver (FLAC/WAV). Plain SaveAudio is deprecated."),
    ("SaveText", "core", "present", "A", "Required for any STRING that must reach the output manifest."),
    ("AudioAmplify", "AudioTools", "reported", "B", "gain_db, per-stem staging."),
    ("AudioPad", "AudioTools", "reported", "B", "pad_start/end_seconds — the timed-placement primitive for spot effects."),
    ("AudioTrim", "AudioTools", "reported", "B", None),
    ("AudioConcat", "AudioTools", "reported", "B", "direction after/before; NO crossfade parameter."),
    ("AudioDelay", "AudioTools", "reported", "B", "Echo effect (delay_ms/feedback/mix), not a timeline shift."),
    ("AudioNormalize", "AudioTools", "reported", "B", None),
    ("AudioBPMDetector", "AudioTools", "reported", "B", "Tempo only — not onsets."),
    ("AudioReactiveParam", "AudioTools", "reported", "B", "AUDIO->FLOAT amplitude envelope; not onset segmentation."),
    ("FB_Qwen3TTSVoiceDesign", "Qwen3-TTS", "reported", "B", "Designed voice via instruct text; cloud-safe no-audio-input VO alternative. Output rate UNMEASURED."),
    ("FB_Qwen3TTSDialogueInference", "Qwen3-TTS", "reported", "B", "Multi-speaker."),
    ("sample-rate-conversion node", "-", "absent", "B", "NO explicit SRC node on the allowlist (agent-verified search). 48 kHz is not an exposed knob in-graph."),
    ("shot-boundary / onset detector", "-", "absent", "B", "None on allowlist. Spot-effect timing must come host-side."),
    ("audio pan node", "-", "absent", "B", "None found."),
    ("float math / clamp node", "-", "unknown", "B", "Asked in round 4 (F5). If absent, bed duration stays a manual knob."),
]

MODELS = [
    # (file/name, loader, license, commercial, cls, notes)
    ("acestep_v1.5_xl_base_bf16.safetensors", "UNETLoader", "MIT (code+weights)", "yes", "A", "The measured production bed/music model. Recipe: euler/simple/50/cfg6 + AuraFlow shift 3; 48 kHz decode; 60 s production window."),
    ("ace_1.5_vae.safetensors", "VAELoader", "MIT", "yes", "A", None),
    ("qwen_0.6b_ace15.safetensors", "CLIPLoader/DualCLIPLoader type=ace", "MIT", "yes", "A", None),
    ("qwen_4b_ace15.safetensors", "CLIPLoader/DualCLIPLoader type=ace", "MIT", "yes", "A", None),
    ("ace_step_1.5_turbo_aio.safetensors", "CheckpointLoaderSimple", "MIT", "yes", "A", "AIO MODEL+CLIP+VAE. Turbo — sampler must mirror the official turbo template (~8 steps/cfg 1), NOT the XL recipe. Unaudited."),
    ("ace_step_v1_3.5b.safetensors", "CheckpointLoaderSimple", "Apache-2.0", "yes", "A", "ACE 1.0 line (the v1 as-built). Decodes 44.1 kHz. Superseded by 1.5 on quality AND license."),
    ("microsoft/Florence-2-large", "DownloadAndLoadFlorence2Model", "MIT", "yes", "A", "In-Comfy the wrapper manages loading. Native transformers outside Comfy needs florence-community/* conversions."),
    ("Chatterbox (Resemble AI)", "FL_Chatterbox*", "MIT + Perth watermark", "yes", "A", "Cloning consent-gated + local-only (no cloud audio upload). First cloud e2e measured 2026-08-21."),
    ("stable_audio_3_medium.safetensors", "CheckpointLoaderSimple + CLIPLoader t5gemma type=stable_audio", "Stability Community License (<$1M) + Gemma ToU rider", "conditional", "A", "SFX lane. lcm/8/cfg1, 44.1 kHz, ~2.6 cr/10 s. NOT 'permissive' — agent's round-1 claim corrected."),
    ("Qwen3-TTS", "FB_Qwen3TTS*", "Apache-2.0", "yes", "B", "Cloud VO alternative (preset/designed voices). Run one line before relying."),
    ("MMAudio", "local only", "code MIT / weights CC-BY-NC 4.0", "no", "A", "Direct V2A — best sync, commercially blocked. KB wave-verified."),
    ("VHS/AudioTools/Florence2 wrapper packs", "-", "MIT-class wrappers", "yes", "B", "Wrapper license != model weights license. Decisive axis is the weights."),
]

RUNS = [
    # (job_id, date, description, gpu_sec, credits, rate, ch, bits, dur, sha256, cls, source)
    ("26a78ccd-06c3-4618-8822-08a547c7e8e9", "2026-08-19", "Florence-2-large caption, 1 image (caption-florence2-v1)", 6.73, 1.8, None, None, None, None, None, "A", "readouts wave 8, billing feed"),
    ("d3cda2f7-bc64-413e-ae14-dc0d279e5dff", "2026-08-21", "ACE-Step 1.0 SFX demo, 10 s ask, 50 steps (rain ambience)", 7.628, 2.0, 44100, 2, 16, 9.938, "676bbbcbc171261c20198a08044ef992de626f18b472434232680f86f7cc25aa", "A", "billing feed + FLAC STREAMINFO decode"),
    ("19c22524-a7b0-48ee-bb99-37e1651e8067", "2026-08-21", "FL_ChatterboxTTS demo line, default voice — FIRST e2e cloud measurement", 6.545, 1.7, 24000, 1, 16, 5.800, "7cf405e338dc8921a560fcdab917e714456056a61c7689f8ac0ed20c2a1fe44b", "A", "billing feed + FLAC STREAMINFO decode"),
    ("b81c6dbf-confirmation", "2026-08-18", "ACE 1.5 XL 120 s track + Demucs 4-stem (Motif builds v2 confirmation)", 29.7, 7.9, 48000, 2, 16, 120.0, None, "A", "readouts wave 7 (full UUID in wave receipts)"),
    ("7b966963-confirmation", "2026-08-18", "SA3 Medium SFX 3 s (partial cache); uncached 10 s ~= 9.8 gpu-sec", 1.1, 0.3, 44100, 2, 16, 2.972, None, "A", "readouts wave 7"),
    ("c4d0c2a8-c308-439a-a704-68423cb41c8e", "2026-08-21", "Wan t2v test clip, 5 s attempt (superseded by the 10 s take)", 172.961, 46.0, None, None, None, None, None, "A", "billing feed"),
    ("1c4e02a8-0a7f-4806-b548-201160f42530", "2026-08-21", "Wan t2v AUDITION CLIP: 10 s photorealistic rain/cyborg, silent — 161 frames @ 16 fps, h264, no audio track", 511.712, 136.0, None, None, None, 10.062, "9985a8ba6197ea7c02adc99c4c3aafc2a9d1cfa13e535ede64908ebea327a30c", "A", "billing feed + local MP4 atom probe"),
]

GRAPHS = [
    # (name, location, workflow_id, nodes, status, cls, notes)
    ("Describe a video (Florence2) [v1]", "workflows/comfy-cloud/as-built/describe-a-video-florence2.json + cloud file", None, 13, "archived; superseded", "A", "Agent's v1 full chain. 10-item defect ledger in as-built README."),
    ("Demo: SFX (ACE-Step)", "workflows/comfy-cloud/as-built/demo-sfx-ace-step.json + cloud record", "0a8b29f6-c16c-4cd4-91ce-69d12bba1cc8", 7, "archived; ran 1x", "A", None),
    ("Demo: Dialogue (ChatterBox)", "workflows/comfy-cloud/as-built/demo-dialogue-chatterbox.json + cloud record", "843f8a61-e3a4-412e-b349-333fa827f290", 2, "archived; ran 1x", "A", None),
    ("fx-dub v2", "workflows/comfy-cloud/as-built/fx-dub-v2.json (editor) + .api.json + RESTORED cloud record", "65a063a5-9342-4297-8cfa-01313178fab9", 29, "archived + restored server-side; superseded by v2.1 order", "A", "Defects F1-F5. The original file 'fx-dub v2.json' was CLOBBERED by the agent's open_workflow (now holds a 19-node Motif dup) — restored copy lives at the workflow_id here."),
    ("Motif builds v2 (reference)", "readouts model-knowledge/workflows/audio/ace15-track-to-stems.json + cloud record", "78a76ecd-7ae2-452a-afea-ad55a8d290f8", 19, "measured reference — DO NOT MODIFY", "A", "The receipt-verified ACE 1.5 XL stack: UNETLoader+VAELoader+DualCLIPLoader(ace), ConditioningZeroOut negative, EmptyAceStep1.5LatentAudio."),
    ("fx-dub v2.1", "workflows/comfy-cloud/as-built/fx-dub-v2.1.json + cloud file 'fx-dub v2.1.json'", None, 34, "SUPERSEDED by v2.2 (its VHS loader cannot reach the asset namespace); wire-verified clean; never run", "A", "XL split stack (UNET+VAE+DualCLIP type=ace), ConditioningZeroOut negative, EmptyAceStep1.5LatentAudio, VHS_SelectEveryNthImage(30) on the Florence branch only, mux reads full loader stream. Open drift: Florence task = detailed_caption (spec said more_detailed_caption); duration knob manual (no float-math node on the allowlist)."),
    ("Ref: fx-dub v2 (mirror source)", "cloud throwaway tab", None, 29, "throwaway; safe to delete", "A", "The agent's read-only mirror tab — its open_workflow went here, not onto a live tab (standing rule honored)."),
    ("fx-dub v2.2", "cloud file 'fx-dub v2.2.json' (29,884 B)", None, 34, "BUILT + wire-verified clean; loader CLEARED; never run; THE AUDITION GRAPH", "A", "The ingest fix: LoadVideo(ea68c5aa....mp4) -> GetVideoComponents -> IMAGE to BOTH VHS_SelectEveryNthImage(30) and VHS_VideoCombine.images. VHS_VideoInfo + VHS_LoadVideo removed; GetVideoComponents fps/AUDIO outputs deliberately unconnected. PrimitiveFloat 16.0 -> VHS_VideoCombine.frame_rate VERIFIED on input slot 4 (link 718920623009028) — closes the round-6 deferred check. Florence drift FIXED (more_detailed_caption). All 7 prefixes under fxdub22/. Loader asset confirmed byte-identical to the local fixture via get_output + local probe. Open: Florence2Run.control_after_generate=randomize (should be fixed)."),
    ("fx-dub v2.1-turbo", "cloud file 'fx-dub v2.1-turbo.json' (29,545 B)", None, 34, "REBUILT + wire-verified clean; cleared to run; never run; the A/B partner to v2.2", "A", "Round-10 rebuild verified value-by-value against v2.2: EXACTLY THREE VALUES DIFFER — UNETLoader.unet_name=acestep_v1.5_xl_turbo_bf16.safetensors, KSampler.steps=8, KSampler.cfg=1, all three matching the official audio_ace_step1_5_xl_turbo template. CheckpointLoaderSimple removed, split stack restored, 34 nodes. Everything else identical incl. AuraFlow shift 3, euler/simple/denoise 1, encoder cfg_scale 2, the shared seed, the mix bus, the same LoadVideo clip, and the 16.0 frame_rate pin on slot 4. All 7 prefixes under fxdubturbo/. NAME LAGS LINEAGE: built on v2.2's ingest, not v2.1's; the agent has no rename tool."),
]

THREADS = [
    # (round, direction, files, state, summary)
    (1, "inbound", "readouts dialogs 2026-08-21-fxdub-01-{transcript,verification}.md", "closed", "Director-run dialog: v1 build + 2 demos. Graphs pulled, demos verified from billing + headers."),
    (2, "outbound+reply", "…-02-{brief,reply,verification}.md", "closed", "v2 build order -> agent delivered 29-node v2; loader claim REFUTED Class A; 3 blockers found."),
    (3, "outbound+reply", "…-03-brief.md + 03-reply (clobber incident)", "closed", "v2.1 fix order -> agent clobbered the v2 tab via open_workflow mid-execution; stopped and asked before proceeding."),
    (4, "outbound+reply", "…-04-{brief,reply,verification}.md", "closed", "GO for v2.1 -> agent built it (33 nodes, validate-only honored, open_workflow used only into a throwaway tab). Verified clean our side: F1-F6 all genuinely fixed."),
    (5, "outbound+reply", "…-05-brief.md + reply", "closed", "2 drift items + audition blockers raised. Agent fixed the Florence task, answered Q1 (no outputs->inputs path exists) and Q2 (ffprobe reads a clean 16/1 from the track; could not see the movie header; recommended pinning frame_rate) — honest about what it could not verify."),
    (6, "outbound+reply", "…-06-brief.md + reply", "closed", "Pin ordered and DONE: agent wired PrimitiveFloat 16.0 -> frame_rate (verified our side: 34 nodes, node 421351014920351 = 16.0), kept VHS_VideoInfo in-graph, recorded the fixture-specific caveat, ran nothing, left the loader untouched."),
    (7, "outbound+reply", "…-07-brief.md + reply", "closed", "Disambiguation: a relayed job-id + output URL were mistaken for an instruction; agent correctly refused to infer one and asked. Confirmed our side the upload had NOT landed (VHS_LoadVideo video COMBO = ['bedroom.mp4']). Agent acknowledged and held: loader untouched, no run, no re-validate."),
    (8, "outbound+reply", "…-08-{brief,reply}.md", "closed", "Director green-lit the turbo tab. Ordered `fx-dub v2.1-turbo` as a CONTROLLED A/B: exact copy of v2.1 with only the generator block swapped (CheckpointLoaderSimple ace_step_1.5_turbo_aio + the OFFICIAL turbo template's sampler settings, read not guessed) and filename_prefix -> fxdubturbo/* so artifacts never collide. Everything else held constant. Validate-only; both tabs audition together on the same clip."),
    (9, "outbound+reply", "…-09-{brief,reply,verification}.md", "closed", "Agent's loader-set attempt was REJECTED by the platform and it reported the rejection honestly. Root cause found our side: TWO video namespaces (VHS input folder = ['bedroom.mp4'] vs core LoadVideo asset namespace = 9 mp4s holding the attachment). Ordered `fx-dub v2.2`: core LoadVideo -> GetVideoComponents -> the existing IMAGE consumers, VHS_VideoInfo removed, 16.0 pin retained, fxdub22/* prefixes. Agent must IDENTIFY the right asset by probe (161 frames / 16 fps / 10.0625 s / no audio) and stop if none match. REPLY: agent built v2.2 (34 nodes, ready_to_run, 0 errors) and identified the asset CORRECTLY, declaring an honest gap (per-stream frames/fps were truncated before it could read them). WE THEN CALLED ITS LOADER VALUE A HARD BLOCKER AND WERE WRONG — see traps. get_output + a local probe confirmed the asset byte-identical to the fixture and closed the agent's gap for it."),
    (10, "outbound+reply", "…-10-{brief,reply,verification}.md", "closed", "Correction round. (1) Told the agent on the record that its asset ID was right and ours was the error, and closed its declared gap with our own measurement (161 frames / 10.0625 s / no audio / 16.000 fps / byte-identical). (2) Gave the REAL turbo recipe read from the official template audio_ace_step1_5_xl_turbo — restore the SPLIT stack, change only unet_name -> acestep_v1.5_xl_turbo_bf16, steps -> 8, cfg -> 1 — and told it round 8's CheckpointLoaderSimple instruction was our mistake and that its relay was truncated on our side. (3) Rename the turbo tab to fx-dub v2.2-turbo (it was copied from v2.2). (4) Set Florence2Run.control_after_generate to fixed in both tabs. (5) Asked whether FL_ChatterboxTTS treats seed 0 as a literal or a randomize sentinel, with an explicit 'cannot determine' allowed. REPLY: turbo tab rebuilt correctly — verified value-by-value, EXACTLY the three-value delta, 34 nodes, split stack restored. Agent answered 'cannot determine' on the Chatterbox seed as invited, and correctly reported that Florence2Run has NO control_after_generate schema input, so OUR round-10 instruction was the unactionable one — item dropped. No rename tool, so the turbo tab's name still lags its lineage. Both graphs cleared to run."),
]

TRAPS = [
    ("A checkpoint loader's COMBO is not the catalog — split-file diffusion models live under UNETLoader/VAELoader/CLIPLoader. Searching CheckpointLoaderSimple alone produced a false 'files not installed' claim.", "high", "A"),
    ("The in-app agent's open_workflow REPLACES the focused tab's canvas AND its saved file — destructive. Standing rule: open references in a NEW tab, or read them over the API instead.", "high", "A"),
    ("Wiring the SAME conditioning output to KSampler positive AND negative cancels CFG algebraically (neg + cfg*(pos-neg) = pos). Use ConditioningZeroOut (the reference stack's negative).", "high", "A"),
    ("VHS_LoadVideo's frame knobs (skip_first_frames/frame_load_cap) act on its ONE image stream — a cap for the captioner also starves VHS_VideoCombine. Subsample the Florence branch only (VHS_SelectEveryNthImage).", "high", "A"),
    ("frame_load_cap=0 + select_every_nth=1 sends EVERY frame to Florence-2 — a 60 s clip is ~1,700 captioned frames of GPU time.", "medium", "A"),
    ("ACE 1.0 decodes 44.1 kHz stereo; cloud Chatterbox decodes 24 kHz MONO; ACE 1.5 mix decodes 48 kHz. Never combine without conforming channels (AudioStandardize) — and there is NO SRC node, so measure the mix output rate from the FLAC header.", "high", "A"),
    ("SaveAudio (FLAC) is deprecated — masters go through SaveAudioAdvanced. MP3 padding breaks alignment.", "medium", "A"),
    ("STRING outputs (caption, loudness_info) reach the output manifest ONLY through SaveText — dangling STRINGs are lost headlessly.", "medium", "A"),
    ("Florence2Run do_sample=true breaks caption reproducibility and forfeits memo-cache pricing. Pin do_sample=false + fixed seed.", "medium", "A"),
    ("Editor-valid != API-valid: COMBO values are TYPE-strict at /api/prompt ('4' passes, 4 fails); UI-only nodes vanish headlessly. Graphs must be static-validation green.", "high", "A"),
    ("timesignature is a STRING COMBO ('2','3','4','6') — 2/4 is the silent default; keyscale is a 34-value major/minor enum (modes are rejections).", "medium", "A"),
    ("Cloud has NO audio-upload path: any node needing reference AUDIO (cloning, DialogTTS) is local-only.", "high", "A"),
    ("Pinned-seed byte-identity is memo-cache-only; a fresh re-execution reproduces the sound, not the bytes. Treat downloaded masters as canonical-by-hash.", "medium", "A"),
    ("The account-wide queue caps at 100 jobs — serialize batch submission (readouts trap ledger, measured on the library burn).", "medium", "A"),
    ("Turbo checkpoints need the turbo template's sampler (~8 steps/cfg 1) — running the XL recipe (50/cfg 6) on a turbo AIO overbakes at ~6x cost.", "medium", "B"),
    ("Video generation dwarfs the whole audio pipeline: one 10 s Wan t2v clip cost 511.7 gpu-sec (~136 cr) vs ~10 cr for a full fx-dub audio run. Never generate test footage casually — reuse the archived audition clip.", "high", "A"),
    ("The Wan-generated audition clip's mvhd movie timescale is 0 (malformed movie header; the per-track mdhd is correct at 16384/164864 = 10.062 s). VHS_VideoInfo.source_fps feeds VHS_VideoCombine.frame_rate — if fps derivation reads the movie header it may emit 0/NaN and produce a broken dub. VERIFY source_fps == 16.0 at the audition run before trusting the mux.", "high", "A"),
    ("An agent reporting 'this node has no X widget in its schema' can be wrong — the pulled graph JSON is the arbiter. v2.1's VHS_VideoCombine DOES carry pix_fmt/crf/save_metadata/trim_to_audio (verified in widgets_values), despite the agent reporting them absent.", "medium", "A"),
    ("Unrequested spec drift hides inside a correct-looking fix list: v2.1 silently changed the Florence task from more_detailed_caption to detailed_caption while reporting the Florence block 'carried over'. Diff widget values, not just topology.", "medium", "A"),
    ("There is NO video-into-inputs path over the API, in either toolset: the MCP's upload_file is image-only (.jpg/.jpeg/.png/.webp/.gif; an .mp4 is rejected validation.input) and the in-app agent has no route that writes to the inputs namespace. Video fixtures MUST be uploaded through the Comfy Cloud browser UI.", "high", "A"),
    ("Two probes reading DIFFERENT fields of the same file are not a contradiction: ffprobe reported a clean 16/1 from the TRACK while our atom probe found mvhd (MOVIE header) timescale 0. Both true. When a derived value could read either field, pin a primitive rather than betting on which one the node uses.", "medium", "A"),
    ("A bare id or URL pasted into an agent thread is NOT an instruction. A job id (billing/provenance) is not a workflow id and is not openable; a signed output URL cannot reach the inputs namespace. Label every reference as reference, and state the instruction in words.", "medium", "A"),
    ("`VHS_LoadVideo`'s `video` COMBO options ARE the live input-folder listing — read it with get_node to check whether an upload landed and to recover the exact filename, instead of relaying a filename by hand. (Measured 2026-08-21: options were exactly ['bedroom.mp4'], proving the audition upload had not happened.)", "medium", "A"),
    ("THERE ARE TWO VIDEO NAMESPACES AND THEY ARE NOT THE SAME. `VHS_LoadVideo.video` reads the VHS input folder (measured: only ['bedroom.mp4']); core `LoadVideo.file` reads the asset/attachment namespace (measured: 9 content-addressed .mp4s). An attachment can be present in one and invisible to the other — which is exactly what blocked the audition. Check BOTH before concluding a file is unreachable.", "high", "A"),
    ("`GetVideoComponents` (core, category video) converts VIDEO -> IMAGE + AUDIO + framerate FLOAT + bit-depth INT. It is the bridge from the asset-namespace `LoadVideo` to any IMAGE-consuming graph, and removes the dependency on the VHS input folder entirely — the better architecture for a published tool, since users' footage arrives via attachment.", "high", "A"),
    ("ABSENCE FROM A COMBO LISTING IS NOT PROOF OF INVALIDITY. get_node('LoadVideo').file enumerates the INPUT/attachment namespace; a cloud SaveVideo output lives in comfy-cloud-assets under a storage key that LoadVideo resolves but that COMBO never lists. We called a correct loader value a hard blocker on this basis and were WRONG. The authoritative job->asset mapping is get_output(prompt_id); the platform validator's ready_to_run is a stronger probe than our enumeration.", "high", "A"),
    ("The cloud storage key and the sha256 of the bytes are TWO DIFFERENT ADDRESSES FOR ONE FILE. Asset ea68c5aa....mp4 downloads to bytes whose sha256 is 9985a8ba... — byte-identical to our local fixture. Local hash matching against cloud asset names therefore always fails and proves nothing. Map job->asset with get_output, THEN download and hash.", "high", "A"),
    ("estimate_credits is a PRICING pass, not a validator. A minimal LoadVideo->GetVideoComponents->SaveImage graph prices identically (0 credits, no error) whether given a valid or an invalid COMBO value. Never use it to adjudicate graph validity.", "medium", "A"),
    ("A stale widget value sits UNDER every live link and wins the moment the link is cut. v2.2's VHS_VideoCombine.frame_rate widget still reads 8 beneath the PrimitiveFloat 16.0 link: cut that link and 161 frames silently render as a 20.1 s video against a 10 s bed, with no error. Same pattern (harmless while linked) on TextEncodeAceStepAudio1.5.duration=120, EmptyAceStep1.5LatentAudio.seconds=120, KSampler.seed=0, FL_ChatterboxTTS.text. Verify LINK PRESENCE, not widget value.", "high", "A"),
    ("The OFFICIAL ACE-Step 1.5 turbo template (audio_ace_step1_5_xl_turbo, 13 nodes) keeps the SPLIT stack: UNETLoader(acestep_v1.5_xl_turbo_bf16.safetensors) + VAELoader(ace_1.5_vae) + DualCLIPLoader(qwen_0.6b/qwen_4b, type=ace). It does NOT use CheckpointLoaderSimple or an AIO checkpoint. Sampler: steps 8, cfg 1, euler, simple, denoise 1; AuraFlow shift 3 unchanged; encoder cfg_scale 2 unchanged. base->turbo is a THREE-VALUE delta (unet_name, steps, cfg) — a genuinely controlled A/B. Our round-8 CheckpointLoaderSimple instruction was wrong.", "high", "A"),
    ("The editor graph and the node SCHEMA are different views, and a value visible in one may not be settable through the other. Florence2Run's widgets_values carries control_after_generate='randomize', but the node's inputs array has NO such entry — there is no API target to set. We ordered the agent to change it; it correctly refused to invent a target. Same shape as the LoadVideo COMBO error: check the schema before ordering a change to something you only saw in widgets_values.", "medium", "A"),
    ("NEVER hand-transcribe a pulled graph JSON from context into an archive file. A 30 KB graph is thousands of numeric node and link ids; one transposed digit produces an archive that silently LIES to every future session. Archiving requires a direct pull-to-disk path. Prose verification records are safe; hand-copied JSON is not.", "high", "A"),
    ("The in-app agent's replies have twice arrived DEGRADED: round 8 was truncated mid-instruction (it declared a placeholder rather than guessing — correct), and rounds 8+10 came back with tab and node names flattened to the literal strings 'node' and 'fx-dub the model'. Never resolve a garbled or truncated reference by inference. Pull the graph and look.", "medium", "A"),
]

DECISIONS = [
    # (id, choice, findings)
    ("A", "Caption-mediated pipeline by design; v1 targets ambience/dialogue-grade sync and says so. Timing never comes from richer captions.", "dispatch findings 1-3, 13"),
    ("B", "Three-layer output (bed / spots / dialogue) mixed from stems, never a single generated mix.", "7, 38, 44"),
    ("C", "Bed <= 60 s single window; longer videos segment at shot boundaries with overlap+crossfade; min segment 2 s.", "4, 5, 6 + prompt-lab 60 s ceiling"),
    ("D", "Deterministic SUBTRACTIVE caption->audio-prompt rewrite stage (temperature 0, pinned, cached). Host-side Ollama or manual box on cloud.", "9-12, 14-17"),
    ("E", "Dialogue is human-authored, never generated from the caption.", "21 + house rule"),
    ("F", "Mix: 48 kHz bus target, dialogue anchor, bed -15 LU (ambience) / -10 LU (music), integrated -18 LUFS, TP -1 dBTP; offsets exposed; manifest reports BS.1770 rev, gated+ungated LUFS, TP, LRA, SBLD<4LU windows.", "28-36"),
    ("G", "Governance as feature: consent-gated local-only cloning, Perth stays on, manifest = Art.50 machine-readable mark, no person-specific voice packs, no robocalls.", "19-27"),
    ("H", "Dub kit deliverables: dubbed.mp4 + mix.flac + stems/ + caption.txt + audio_prompt.txt + manifest.json.", "37-44"),
    ("I", "Model lanes: MIT default (ACE 1.5 + Chatterbox + Florence-2); SA3 conditional lane; direct-V2A non-commercial lane; Qwen3-TTS Apache cloud VO alt.", "KB license wall"),
    ("J", "External verification at every layer: graphs validation-green, audio verified by meters, citations by different-family verifier, agent claims re-verified over the API before acting.", "protocol"),
]

NEXT_ACTIONS = [
    ("RESOLVED 2026-08-22: no upload was ever needed. The clip is already reachable as cloud asset ea68c5aa....mp4, byte-identical to the local fixture (confirmed via get_output + local probe). fx-dub v2.2's loader is CLEARED.", "Director", "done"),
    ("RESOLVED 2026-08-22: the PrimitiveFloat 16.0 -> VHS_VideoCombine.frame_rate link is VERIFIED present on input slot 4 of fx-dub v2.2 (link 718920623009028; api_format resolves to the link, not a literal). The round-6 deferred check is closed.", "advisor session", "done"),
    ("DONE 2026-08-22: round-10 brief relayed; turbo tab rebuilt and verified value-by-value against v2.2 — exactly three values differ (unet_name / steps 8 / cfg 1), matching the official template. Both graphs cleared to run.", "Director + advisor", "done"),
    ("ORDER THE AUDITION: BOTH fx-dub v2.2 (base, 50 steps/cfg 6) and fx-dub v2.1-turbo (turbo, 8 steps/cfg 1) are cleared, verified, and pointed at the same clip with the same seed. Run them together for the cost/quality A/B (~10-15 cr for the base; the turbo should be materially cheaper). Nothing else blocks it.", "Director", "open"),
    ("Archive fx-dub v2.2 + v2.1-turbo JSON to workflows/comfy-cloud/as-built/ and repoint the graph_lint forward gate at v2.2 (the archived v2.1 is a 33-node PRE-PIN snapshot, now superseded). DO NOT hand-transcribe the JSON from a pull — see the trap; this needs a direct pull-to-disk path.", "advisor session", "open"),
    ("Add a graph_lint detector for the mux frame_rate trap: VHS_VideoCombine.frame_rate must be LINK-driven, never a bare widget (the widget beneath the live link reads 8; cutting the link silently yields a 20.1 s dub). Note the control_after_generate detector idea is DROPPED — Florence2Run has no such schema input, so there is nothing to lint.", "advisor session", "open"),
    ("After the audition run: download all 7 artifacts to one dir and run `python tools/audition_receipt.py <dir> --json receipt.json`; commit the receipt; fold the measured mix sample rate into the KB (settles the open mix-bus question) and into the next readouts wave", "advisor session", "open"),
    ("SUPERSEDED 2026-08-22 by the v2.2+turbo audition action above (v2.1 is no longer the audition graph). The post-run measurements it named still stand and are carried by tools/audition_receipt.py: decode the mix FLAC header (SETTLES the mix-bus sample-rate question), read both LUFS manifests, and confirm the dub carries an audio track.", "Director + advisor", "done"),
    ("Fold ChatterBox/ACE-1.0 measurements into the next readouts model-knowledge wave", "advisor session", "open"),
    ("Gate the prompt-craft audio-domain dispatch's citations through roleos verify-citations -> prism BEFORE any finding becomes canon (its own standards table scores EXTERNAL_VERIFIER 1 for this reason)", "next session", "open"),
    ("Build prompt-craft `domains/audio` per docs/design/2026-08-21-promptcraft-audio-domain.dispatch.md (A1-A7) — additive plugin + one register call, core/ unchanged; respect the identity-subgate fences", "next session", "open"),
    ("Host-side rewrite runner (Ollama, deterministic, cached) — decision D, superseded in spirit by the prompt-craft audio plugin", "future session", "open"),
    ("Spot-effects event timeline (host-side shot/onset detection -> AudioPad placements)", "future session", "open"),
    ("Local-lane graphs (5090) mirroring the cloud stack", "future session", "open"),
    ("npm name 'fx-dub' unverified — reserve via trusted-publishing flow at ship time", "future session", "open"),
]

def main():
    # Drop-and-recreate in place rather than deleting the file: on Windows an open
    # reader (a test, a DB browser) holds a lock and os.remove raises WinError 32.
    c = sqlite3.connect(DB)
    for kind, name in c.execute(
        "SELECT type, name FROM sqlite_master WHERE type IN ('view','table') AND name NOT LIKE 'sqlite_%'"
    ).fetchall():
        c.execute("DROP {0} IF EXISTS \"{1}\"".format("VIEW" if kind == "view" else "TABLE", name))
    c.commit()
    c.executescript("""
    CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE nodes(name TEXT PRIMARY KEY, pack TEXT, status TEXT, class TEXT, notes TEXT);
    CREATE TABLE models(name TEXT PRIMARY KEY, loader TEXT, license TEXT, commercial TEXT, class TEXT, notes TEXT);
    CREATE TABLE runs(job_id TEXT PRIMARY KEY, date TEXT, description TEXT, gpu_sec REAL, credits_approx REAL,
                      sample_rate INTEGER, channels INTEGER, bits INTEGER, duration_s REAL, sha256 TEXT, class TEXT, source TEXT);
    CREATE TABLE graphs(name TEXT PRIMARY KEY, location TEXT, workflow_id TEXT, nodes INTEGER, status TEXT, class TEXT, notes TEXT);
    CREATE TABLE threads(round INTEGER PRIMARY KEY, direction TEXT, files TEXT, state TEXT, summary TEXT);
    CREATE TABLE traps(id INTEGER PRIMARY KEY AUTOINCREMENT, trap TEXT, severity TEXT, class TEXT);
    CREATE TABLE decisions(id TEXT PRIMARY KEY, choice TEXT, findings TEXT);
    CREATE TABLE next_actions(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, owner TEXT, status TEXT);
    CREATE VIRTUAL TABLE fts USING fts5(kind, name, body);
    CREATE VIEW v_open_actions AS SELECT * FROM next_actions WHERE status='open';
    CREATE VIEW v_publishable AS SELECT name, license, notes FROM models WHERE commercial='yes';
    CREATE VIEW v_measured_costs AS SELECT description, gpu_sec, credits_approx, date FROM runs ORDER BY date;
    """)
    c.executemany("INSERT INTO nodes VALUES(?,?,?,?,?)", NODES)
    c.executemany("INSERT INTO models VALUES(?,?,?,?,?,?)", MODELS)
    c.executemany("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", RUNS)
    c.executemany("INSERT INTO graphs VALUES(?,?,?,?,?,?,?)", GRAPHS)
    c.executemany("INSERT INTO threads VALUES(?,?,?,?,?)", THREADS)
    c.executemany("INSERT INTO traps(trap,severity,class) VALUES(?,?,?)", TRAPS)
    c.executemany("INSERT INTO decisions VALUES(?,?,?)", DECISIONS)
    c.executemany("INSERT INTO next_actions(action,owner,status) VALUES(?,?,?)", NEXT_ACTIONS)
    for kind, rows, keyf, bodyf in [
        ("node", NODES, lambda r: r[0], lambda r: " ".join(str(x) for x in r[1:] if x)),
        ("model", MODELS, lambda r: r[0], lambda r: " ".join(str(x) for x in r[1:] if x)),
        ("run", RUNS, lambda r: r[0], lambda r: " ".join(str(x) for x in r[1:] if x)),
        ("graph", GRAPHS, lambda r: r[0], lambda r: " ".join(str(x) for x in r[1:] if x)),
        ("trap", TRAPS, lambda r: r[0][:60], lambda r: r[0]),
        ("decision", DECISIONS, lambda r: r[0], lambda r: r[1] + " " + r[2]),
        ("action", NEXT_ACTIONS, lambda r: r[0][:60], lambda r: " ".join(r[:2])),
    ]:
        c.executemany("INSERT INTO fts VALUES(?,?,?)", [(kind, keyf(r), bodyf(r)) for r in rows])
    c.execute("INSERT INTO meta VALUES('schema_version','1')")
    c.execute("INSERT INTO meta VALUES('built_at',?)", (datetime.date.today().isoformat(),))
    c.execute("INSERT INTO meta VALUES('rule','Rebuild by editing the seed data in build_db.py and rerunning; commit script + db together. Rows: class A=measured, B=advisory; 30-day freshness rule applies.')")
    c.commit()
    for t in ("nodes","models","runs","graphs","threads","traps","decisions","next_actions"):
        print(t, c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    c.close()
    print("wrote", DB)

if __name__ == "__main__":
    main()
