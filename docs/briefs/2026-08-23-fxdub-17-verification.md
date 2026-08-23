# fx-dub round 17 — verification (ours)

Paired with [`2026-08-23-fxdub-17-reply.md`](2026-08-23-fxdub-17-reply.md).

**Round scoreboard: our defects 1, the agent's 0.** The defect is a big one — we relayed a false
finding, and the agent has logged it as fact.

## 1. ⛔ RETRACTED: round 17 §5.2 was wrong

We told the agent, in a relayed brief: *"the take our handoff names as the delivered MAC is **not**
the one in the delivered mix."* It logged that faithfully as our open action.

**It is false. The handoff was right and we were wrong.** Proven by byte-identity, four free jobs,
2026-08-23:

| Step | Rebuilt from | FLAC STREAMINFO md5 | Target |
|---|---|---|---|
| assembled VO | `AudioMix(b7066f85…, place(d7ba748c…, 2.30 s))` | `e65dc817…` | **matches `8eadf234…`** |
| delivered `stem_vo` | that VO through `AudioAdjustVolume(+7)` | `b2816092…` | **matches** |
| delivered `mix` | that plus bed `d8ef106a…` at `gain_1_db −12` | `c34976a8…` | **matches** |

**There is no third key.** The whole delivered run reproduces from three storage keys, exactly.

### How we got it wrong

We read the diarized word timings — MAC at **2.279–3.959 s**, so ~1.68 s of speech — as a
*measurement of the clip's extent*, and used it to rule out a 1.415 s artifact.

They are a transcription model's boundary estimates. The clip truly spans **2.300–3.715 s**; the
diarizer ran 0.021 s early at the head and **0.244 s late at the tail**. That overshoot was the
whole basis of the "discrepancy."

**We used a model's output to contradict a byte-level fact, and published the contradiction before
testing it** — into `HANDOFF.md`, a relayed brief, the CHANGELOG of a released version, and the KB.
All four are corrected; the CHANGELOG keeps the wrong claim struck through rather than deleted,
because the released 1.1.0 notes carry it and hiding the error destroys the evidence of how it was
made.

The sharpest part: this is the **same class of error as the caption hallucination** we spent the
release documenting — trusting a model's output as a measurement. We made it while writing that up.

**Trap earned:** *diarized word timings are correct enough to gate CONTENT (order, overlap, gaps)
and too loose to establish an artifact's EXTENT. For extent, decode the file.*

## 2. Two findings that came out of the same four jobs

- **The whole run is reproducible from three keys**, byte-exact at every hop. The FLAC md5 sits in
  STREAMINFO bytes 18–34 and needs no decoder, so equality is a free local test. This is now the
  preferred way to prove a rebuild — stronger than a duration match, which is what misled us.
- **The deliverables sit at different points in the gain chain.** `stem_vo` ships **post**-gain
  (+7 dB already applied); the bed stem ships **pre**-gain and the mix applies −12 dB on the bus.
  That asymmetry is exactly what `--bed-gain-db` exists to compensate, and why the −9 default
  reports this run's ducking depth 3 LU low. Do not assume "stem" means pre-gain.

## 3. What the agent got right, unprompted

It identified the §3/§8 pairing as the real lesson rather than either half alone — *"a receipt that
checks 161 frames intact on the intermediate fails on every correct run"* — which is precisely the
design correction, stated better than our own brief stated it.

It also volunteered the detection method for the silent-clamp trap: **identical content hashes on
two distinct indices means clamping.** That is how we caught it, and it had to infer that from the
symptom alone.

## 4. Outstanding on our side

The agent is carrying our false §5.2 as a logged fact. **The next outbound round must open with the
retraction** — before anything else, because it recorded it as our open action and will otherwise
keep treating it as live.

## 5. State

Traps **86 → 89** (one *replaced* by its retraction rather than contradicted — a KB carrying both
readings is worse than either). Open actions **21 → 22**. `verify.sh` PASS, 197 tests.
