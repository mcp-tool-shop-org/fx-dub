# runs/ — measured run artifacts

Every directory here is one **measured** execution, kept as evidence rather than
as output. The rule from `AGENTS.md` applies: a receipt is a measurement, not a
report, so the bytes that produced a finding stay next to the finding.

| Directory | What it is |
|---|---|
| `2026-08-22-audition-01/` | **The first successful fx-dub run in the project's history** (job `678474ca-0bb8-4201-9236-8f65dd5789a8`). All seven artifacts plus `receipt.json` from `tools/audition_receipt.py` — 14/18. `dubbed_00001-audio.mp4` is the proof the re-mux carries an audio track with all 161 frames intact. |
| `2026-08-22-sfx-bakeoff/` | ElevenLabs `eleven_sfx_v2` candidates (job `d8ab8968-fa35-4979-b063-4a9df7121862`). All 48 kHz stereo at exactly 10.000 s. `S5_layered_rain_plus_steps.flac` is rain + footsteps layered at −4 dB, measuring −17.44 LUFS. |
| `2026-08-22-voice-bakeoff/` | Qwen3-TTS and Chatterbox voice candidates (job `6e52b225-b47c-4cd4-b351-5b1fdbc5e972`). All 24 kHz mono — which is *every* TTS option on cloud, and the reason the ambience bed must occupy `AudioMix.audio_1`. |

**Do not regenerate these.** They are cited by `traps` and `runs` rows in
`kb/fxdub.db` with full job UUIDs; re-rolling them would orphan the citations.
