<p align="center">
  <img src="docs/assets/logo.png" alt="fx-dub" width="820">
</p>

#

**Give any video its soundtrack: describe → generate → mix → re-mux.**

fx-dub is a ComfyUI-native pipeline that takes a video clip, describes what's on screen (Florence-2), turns that description into *audio* prompts, generates an ambience/SFX bed (ACE-Step 1.5) and spoken dialogue (Chatterbox), mixes them to an evidence-based loudness target, and muxes the result back onto your video — with stems, a caption/prompt trail, and a loudness+provenance manifest beside every output.

**The publishable lane is MIT end-to-end**: Florence-2 (MIT) → ACE-Step 1.5 (MIT code+weights) → Chatterbox (MIT, Perth-watermarked) → Demucs-class tooling (MIT). Runs on a local GPU or on [Comfy Cloud](https://cloud.comfy.org) — cloud unit costs below are measured on-account, not estimated. Every alternative — cloud/local, permissive/conditional/paid — is mapped honestly in the **[Knowledge Base](docs/knowledge-base.md)**.

```
video ─► describe (Florence-2, deterministic)
              │ caption.txt
              ▼
        rewrite (subtractive: audible content only)
              │ audio_prompt.txt
              ├─────────────► SFX/ambience bed (ACE-Step 1.5, 48 kHz, duration = clip)
              │                        │ stems/bed.flac
   your script (you write it) ──► dialogue (Chatterbox, default voice / consented clone)
                                       │ stems/dialogue.flac (24 k → resampled)
                                       ▼
                          mix bus (48 kHz · dialogue-anchored · −18 LUFS · TP −1 dBTP)
                                       │ mix.flac + manifest.json (BS.1770 report + provenance)
                                       ▼
                          re-mux ─► dubbed.mp4
```

## Status

**v0 — the design is done and verified; the first graphs are being built.** Full history in the [CHANGELOG](CHANGELOG.md).

| Piece | State |
|---|---|
| [Design rationale](docs/design/2026-08-21-fxdub-v1.dispatch.md) — 45 sourced findings behind every default | ✅ citations externally verified ([record](docs/design/2026-08-21-fxdub-v1.dispatch.verify.md), Ed25519 receipt in-repo) |
| [Knowledge Base](docs/knowledge-base.md) — every option, honest licenses, measured costs | ✅ |
| [As-built graphs](workflows/comfy-cloud/as-built/) — the in-app agent's v1, pulled over the API | ✅ archived with a [10-item defect ledger](workflows/comfy-cloud/as-built/README.md) |
| [Agent onboarding](AGENTS.md) + project database ([kb/fxdub.db](kb/README.md)) — nodes, models, runs, traps, decisions, open actions | ✅ live; rebuilt each session |
| As-built v2 — the agent's 29-node rebuild, pulled + wire-verified ([ledger](workflows/comfy-cloud/as-built/README.md)) | ✅ archived + restored server-side after a tab clobber; 3 blockers logged |
| [v2.1 fix brief](docs/briefs/2026-08-21-fxdub-03-brief.md) — restores the measured ACE stack, fixes CFG/frame defects | 📨 awaiting relay |
| v2.1 verification → Director's audition run → host runner, event-timeline spot effects | ⏳ next |

## What's honest about this design

- **Captions carry meaning, not timing.** A caption-mediated pipeline is ambience/dialogue-grade; it will never sync a door-slam by prose alone. Impact-grade timing is an event-timeline feature (roadmap), and the direct video→audio models that do it natively are all non-commercial on open weights — the [KB](docs/knowledge-base.md#stage-2b--direct-videoaudio-the-sync-first-alternative) maps them.
- **A scene description is not a script.** You write the words your characters say; the pipeline makes them sound right.
- **Mix numbers come from standards and listening studies** (BS.1770-5, AES TD1008, JAES ducking research), not vibes — and they're knobs, because preferences measurably differ.
- **Governance is a feature**: consent-gated cloning (local only), the Perth watermark stays on, the manifest doubles as your EU AI Act Art. 50 machine-readable mark, and the [KB's publishing section](docs/knowledge-base.md#publishing--governance-read-before-you-ship-a-dubbed-video) tells you what disclosure you owe where you post. No person-specific voice packs, ever. Not for robocalls.

## Measured unit costs (Comfy Cloud, ≈0.266 cr/gpu-sec)

| Unit | ≈ credits |
|---|---|
| Florence-2 caption | 1.8 |
| 10 s ambience bed (ACE 1.0, as-built demo) | 2.0 |
| One dialogue line (Chatterbox default voice) | 1.7 |
| 10 s SFX (Stable Audio 3 Medium) | 2.6 |
| Ballpark 30 s clip, full v1 pipeline | 8–12 |

## Provenance

This repo practices receipts-first development: graphs are pulled from the platform and verified (billing feed, decoded output headers) rather than trusted from reports; design citations pass an external different-family verifier before they become architecture; measured numbers carry their job UUIDs. Studio knowledge base: `mcp-tool-shop-org` readouts, waves 1–8.

## License

[MIT](LICENSE) — the repo. Model weights carry their own licenses; the [Knowledge Base](docs/knowledge-base.md) is the honest map. © 2026 mcp-tool-shop.
