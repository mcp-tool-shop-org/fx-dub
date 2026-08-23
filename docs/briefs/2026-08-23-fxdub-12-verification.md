# fx-dub round 12 — verification (ours)

Paired with [`2026-08-23-fxdub-12-reply.md`](2026-08-23-fxdub-12-reply.md). Written 2026-08-23.

**Round scoreboard: our defects 3, the agent's 0.** The agent refused three asks and all three
refusals were correct. This is the second consecutive round its count has been lower than ours.

## 1. The three refusals, upheld

| Item | Agent's position | Our verdict |
|---|---|---|
| 5 — MAC's face coordinates | *"genuinely impossible for me… anything I gave you here would be fabricated"* | **UPHELD.** We assigned vision work to a text channel and, worse, called it *"genuinely yours."* The agent has no visual grounding; we have `plain-sight` / `ai-eyes` on this rig and no H.264 decoder. Correct division is *it extracts, we see* — issued as round 13 §4. |
| 4 — runtime slot names | *"I'd be repeating the error you're warning me about"* | **UPHELD.** We asked for runtime-proven names while forbidding the only cheap source (advertised schema) and providing no completed job. Circular. Re-sequenced as an output of the audition. |
| 3 — VIDEO by storage key | *"the honest answer is: unproven. I will not assert yes or no."* | **UPHELD.** Same inversion. We demanded execution-proof as a precondition of the run that produces it. |

Its stated boundary — *treat nothing attributed to my prior self as load-bearing until re-derived
live* — is functionally identical to **trap 33**, which we wrote after rounds 8 and 10. Independent
convergence on the same rule; recorded as such, not as a concession.

## 2. The flattening artifact is real, channel-side, and recurred in this very message — Class A

The agent stated it did not send the five `node` placeholders. **We do not need to adjudicate its
memory, because the artifact reproduced inside its own round-12 reply.** Verbatim from the paste:

- *"by reading `node`'s real schema and checking your 480px / 10.0625s measurements"*
- *"Read `node`'s real schema — confirm sync_mode has a silence value"*
- *"MAC's per-character stem → `node`.audio, sync_mode: silence"*
- *"your rig has no ffmpeg, but `` on this side could pull a frame"* — flattened to **empty**

**This is the fourth and fifth occurrence** (rounds 8, 10, 12-inbound, 12-reply). A message written
to deny sending flattened names arrived containing flattened names. That is decisive evidence the
artifact is introduced by the relay, not authored at either end.

**Consequence:** neither party's transcript of the other is authoritative for *names*. Class names,
storage keys and job ids must be re-derived from the live catalog or `get_output` at the point of
use — never transcribed across this channel. Trap 33 is extended accordingly.

**The "one reason" is formally withdrawn**, not because the agent denied it, but because asking it
to reconstruct text from a degraded relay violated trap 33 on our side. The hard case in round 12
§2 was derived from measurement and stands independently.

## 3. What we measured locally this round — Class A, no credits

From `runs/2026-08-22-v28-bytedance/dubbed_00001-audio.mp4` (MP4 atom parse) and
`runs/2026-08-22-fxvox13-scene-v2/final_verify_words.json` (shipped word timings):

| Quantity | Measured |
|---|---|
| Picture | **832 × 480**, 161 frames, 16.000 fps, 10.0625 s |
| Audio track | 48 kHz, 10.0693 s |
| **MAC's speaking window** | **2.279 s → 3.959 s** (speaker_1, "Not bad. Can't complain.") |
| MAC isolated take (local) | 1.72 s — content only, **not positioned** |
| Shipped VO stem | 9.84 s — carries **both** characters |

**Kling is disqualified on two independent measured axes** — `KlingLipSyncAudioToVideoNode` states
720–1920 px (we are 480 high) and 2–10 s (we are 10.0625 s). Neither is tunable.

**Our round-12 phrasing would have misdirected the build.** We wrote "MAC's stem" as though a
ready artifact existed. What the sync node needs is MAC's line *at its scene position* against the
full timeline. Whether that already exists depends on whether ByteDance's absolute-timeline
behaviour (**trap 58** — a line at `[2.3s:4.0s]` renders ~4.03 s with leading silence written in)
holds for keys `37d38cda…` and `d7ba748c…`. **One `get_output` read settles it; that is round 13's
first ask.** Fallback is `EmptyAudio → AudioConcat`, never `AudioPad` (**trap 57** — broken on
cloud, `UnboundLocalError: pad_samples`).

## 4. Still unproven — do not treat as settled

- `SyncLipSyncNode.video` resolving a cloud storage key with no upload. Strong prior only:
  `LoadVideo` already resolves keys its COMBO omits (**trap 26**), and `get_node("LoadVideo").file`
  currently returns an **empty** options array, the exact shape that finding predicts.
- The runtime dotted-slot names under `model` (`COMFY_DYNAMICCOMBO_V3`). Round 11 precedent:
  advertised `files.item_1`, actual `files.audio0`.
- `sync_mode: silence` behaviour, and whether the pass re-encodes the audio track.
- Lip-sync quality at 16 fps against the node's 24/25/30 advisory, and on profile faces at 480p.

## 5. Traps earned this round

1. **A relay that flattens node names also flattens them in the message denying it.** Names never
   cross this channel authoritatively — re-derive at point of use. (Extends trap 33.)
2. **Do not demand execution-proof as a precondition of the execution that produces it.** Round 12
   made this error three times in one brief. Preconditions and outputs must be separated when
   briefing an agent whose only proof mechanism is a completed job.
3. **Do not assign a capability to a counterparty without establishing it has that capability.**
   "Genuinely yours" was asserted about vision work to a text-only channel.
4. **A per-character *stem* and a per-character *positioned track* are different artifacts.** The
   verifier (`--only-speaker`) consumes the second; saying "stem" sends a builder to the first.
