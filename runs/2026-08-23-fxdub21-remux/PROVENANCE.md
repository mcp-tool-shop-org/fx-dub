# runs/2026-08-23-fxdub21-remux — provenance

The delivered dub with **MAC's mouth driven to his line**, and the shipped mix laid back over it.
Only the PICTURE differs from `runs/2026-08-22-v28-bytedance/`. The audio is provably the same
audio, which is why this directory carries some of that run's files rather than re-measuring them.

## What is new here

| File | Origin |
|---|---|
| `dubbed_lipsynced.mp4` | job `096ce861-32bb-4bf0-bca6-5dc25c790ed2` — key `a76041bc…mp4` |
| `mix_rebuilt.flac` | job `94097e2f-3468-4ecd-87d5-c613e636482c` — key `e60f56de…flac` |

The lip-synced picture it was muxed onto came from job
`4b2339b4-804a-42aa-8198-e2bf89877803` (key `4ff03353…mp4`, ~403 credits): `SyncLipSyncNode`
`sync-3`, `sync_mode: silence`, `speaker_selection: coordinates` at **(348, 122)** on frame 60,
seed 42, driven by the 10.0625 s positioned MAC track `4afc41d2…flac`.

## What is carried over from v28, and why that is sound

`stem_bed_00001.flac`, `stem_vo_00001.flac`, `mix_lufs_00001.txt`, `vo_lufs_00001.txt`,
`bed_lufs_00001.txt`, `caption_00001.txt`.

**These are not stand-ins.** `mix_rebuilt.flac` was rebuilt from the same stem storage keys
(bed `d8ef106a…`, VO `8eadf234…`) through `AudioAdjustVolume(VO, +7)` →
`AudioMix(audio_1=bed, gain_1_db=-12)`, and its FLAC STREAMINFO md5 is
**`c34976a8594c3705cc3622eef75033f6`** — byte-for-byte the delivered v28 mix. The copied stems
were md5-checked against their v28 originals and match:

| File | STREAMINFO md5 |
|---|---|
| `stem_bed_00001.flac` | `493bde61d6d5f987e028164f0f49af1d` |
| `stem_vo_00001.flac` | `b2816092793ef2f896783d1e212ba936` |
| `mix_rebuilt.flac` | `c34976a8594c3705cc3622eef75033f6` |

Since the audio is identical, its meters are identical, so the LUFS manifests describe this run as
accurately as they describe v28. **They were not re-measured here** — that is stated plainly rather
than implied, because a receipt is only worth what its inputs are.

## The caption is wrong, deliberately left as-is

`caption_00001.txt` reads *"two men standing in a city at night, facing each other."* There is
**one** man on screen — decoded frames 20/60/120 show it, and the Director confirmed on 2026-08-23:
*"One man is off camera the entire clip."*

It is kept because it is the record of what the pipeline actually produced, and because the caption
feeds the audio prompt. `audition_receipt` now fails on it:

```bash
python tools/audition_receipt.py runs/2026-08-23-fxdub21-remux --scene docs/scenes/night-street.json --bed-gain-db -12
```

`--bed-gain-db -12` is not optional: the bed meter reads the stem **pre-gain**, and this graph
applies -12 dB on the bus. The tool's -9 default understates the ducking depth as +8.17 LU when it
is really **+11.17 LU**. Gain-stage from the meter, never from a remembered number.

**A failing check is a finding, not a bug in the tool.** Do not regenerate the caption to make the
receipt green.

## Measured deliverable

| | |
|---|---|
| Resolution | 832 × 480 |
| Frames | **161** — the source cadence, restored by the mux round-trip |
| Video track | 10.0625 s |
| Audio track | 10.0693 s |
| Tracks | video + audio both present |

`SyncLipSyncNode` re-times the picture (161 frames @ 16 fps → 473 @ ~47 fps), but
`GetVideoComponents` decodes at the source cadence, so `GetVideoComponents → VHS_VideoCombine`
hands 161 frames back. Assert frame count on the **deliverable**, never on the raw sync output.
