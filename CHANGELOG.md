# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] — 2026-08-23

### Fixed

- **Retracted a false provenance finding published in 1.1.0.** The 1.1.0 notes claimed
  `HANDOFF.md` named the wrong MAC take as the delivered one. It did not — the handoff
  was right. Proven by byte-identity: `AudioMix(b7066f85…, place(d7ba748c…, 2.30 s))`
  reproduces the assembled VO `8eadf234…` **exactly**, that VO at +7 dB reproduces the
  delivered `stem_vo`, and that plus the bed at −12 dB reproduces the delivered mix.
  The whole run rebuilds from three storage keys.

  The error is worth more than the correction: diarized word timings were read as a
  *measurement of a clip’s extent* and used to contradict a byte-level fact. They are a
  transcription model’s boundary estimates — 0.021 s early at the head, 0.244 s late at
  the tail. **Word timings gate content; they do not establish extent.** The 1.1.0 entry
  is struck through rather than deleted, because the released notes carry it and hiding
  the error destroys the evidence of how it was made.

### Added

- `SceneFlagContractTests` — `--scene` shipped in 1.1.0 with the `scene_unreadable` error
  code and **no test coverage**, while the ship gate already claimed those codes were
  covered. Five cases now assert it, including that *no* scene means the caption check is
  **absent** rather than failing: a silently-skipped check that reads as a pass is the
  worse failure mode.
- `ZeroDependencyTests` — the empty runtime dependency list was enforced only in CI, so
  `./verify.sh`, documented as the single local gate, would pass a change CI then
  rejected. Enforced in both places now, and proven able to go red.

### Changed

- `SHIP_GATE.md` records **how** each behavioural skip was re-verified, so the next
  release repeats the walk instead of re-deriving it. `SCORECARD.md` gains a v1.1.0
  re-audit and no longer reads as current.
- 189 → **197 tests**.

## [1.1.0] — 2026-08-23

### Added

- **`fxdub-receipt --scene` and the `caption:person_count_matches_cast` check.**
  The pipeline captions a frame and feeds that caption to the audio prompt, and
  nothing ever compared it back to the picture. On the delivered run the captioner
  wrote *"two men standing in a city at night, facing each other"* over a **one-man**
  shot — and it rode through green, because no audio check can see a picture.

  A zero-dependency package cannot look at pixels. It does not have to: the scene
  contract already states who is visible. The check counts the people the caption
  claims and compares that against the cast members marked `on_frame`. It is
  deliberately shallow — it reads `"<count> <person-word>"` and nothing cleverer —
  and it stays silent when the caption never counts people, because silence is not
  a claim. The delivered run now scores **19/20** and exits 1. That is a finding,
  not a regression.

- **`cast` entries in a scene script are read, not just documented.** `on_frame`
  declares who is visible; `face: {frame, x, y}` carries the pixel coordinates that
  pin lip-sync to a named character. A plain-string cast entry still works — it is
  scanned for `on-frame` / `off-frame`, which the night-street contract already
  carried before the field existed.

- **Picture-stage graph builders in `fxdub.vo_graphs`:** `load_video`,
  `place_exact`, `lipsync`, `mux`, `frames`, and `mix_dialogue_anchored`.

  These exist for the reason the module exists at all. Its docstring records that
  v2.3–v2.7 were lost because they were hand-typed API JSON in a chat window, and
  that session 4 repeated the mistake about fifteen times. Session 5 then did it
  again — through an entire paid run — and only noticed on opening the file and
  finding `place()` and `mix()` already there. A graph you cannot rebuild is an
  anecdote.

- **Three API detectors** behind those builders:
  - `api_lipsync_unpinned_speaker` — `speaker_selection` defaults to *let the model
    decide*. Left unpinned, the job completes, returns a correctly-framed MP4 at the
    right duration, and **passes every container check** with the wrong person's
    mouth moving. This is the container-metrics-cannot-see-content trap arriving in
    the visual domain, where there is no receipt yet.
  - `api_lipsync_resizing_sync_mode` — `bounce`/`loop`/`remap` resize the output to
    the audio length; `remap` time-stretches the picture. Only `silence` leaves the
    delivered duration alone.
  - `api_savevideo_codec_encoding` — `SaveVideo.codec.encoding` crashes local
    pre-flight with `candidate.toLowerCase is not a function` and **no verdict at
    all**, because its options are objects rather than strings.

- `broken` joins the node-status vocabulary. It was needed twice over, and
  `AudioPad`'s row still read `reported`/Class B long after it had been measured
  failing.

### Fixed

- **~~`HANDOFF.md` named the wrong MAC take as the delivered one.~~ RETRACTED
  2026-08-23 — the handoff was right and this entry was wrong.** Proven by
  byte-identity after 1.1.0 shipped: `AudioMix(b7066f85…, place(d7ba748c…, 2.30 s))`
  reproduces the assembled VO `8eadf234…` **exactly**, and that VO at +7 dB
  reproduces the delivered `stem_vo`, which mixed with the bed at −12 dB reproduces
  the delivered mix. There is no third key.

  The error: diarized word timings put MAC at 2.279–3.959 s (~1.68 s), and that was
  read as a *measurement* of the clip's extent and used to contradict a byte-level
  fact. They are a transcription model's boundary estimates — 0.021 s early at the
  head, 0.244 s late at the tail, against a clip that truly spans 2.300–3.715 s.
  Word timings gate **content**; they do not establish **extent**. Left visible
  rather than deleted: the released 1.1.0 CHANGELOG carries the wrong claim, and a
  correction that hides the error destroys the evidence of how it was made.

### Measured

Recorded in `kb/fxdub.db` (traps **65 → 86**, runs **22 → 32**, nodes **40 → 46**):

- **`AudioMix` gains clamp to −24…+6 dB.** The recorded mix recipe of "VO +7 dB"
  could never have come from the bus — it is an `AudioAdjustVolume` node ahead of
  it. Rebuilt that way, the mix came back **byte-identical** to the delivered one
  by FLAC STREAMINFO md5. A recipe that names a gain without naming the node that
  applies it is not reproducible.
- **`AudioVideoCombine` is broken on Comfy Cloud** (`ImportError: TorchCodec`),
  joining `AudioPad`. Mux via `GetVideoComponents → VHS_VideoCombine` instead.
- **Lip-sync re-times the picture** — 161 frames at 16 fps in, 473 at ~47 fps out —
  but `GetVideoComponents` decodes at the source cadence, so the mux round-trip
  hands 161 frames back. Assert frame count on the **deliverable**, never on the
  raw sync output.
- **`ImageFromBatch` clamps an out-of-range index silently** to the last frame, and
  `GetVideoComponents` decodes at the source rate regardless of the container.
  Reading a *named* frame can therefore return a different one with no error.
- A node's schema can differ between two tool surfaces reading the same live
  catalog. Ours returns nine required inputs for the lip-sync node with five
  conditional sub-fields; another returns four and carries no `input_details` at
  all. Round 11 taught *advertised ≠ runtime*; this teaches **advertised ≠
  advertised** — read from a second surface before concluding a field is absent.

## [1.0.1] — 2026-08-22

### Fixed

- **The round-11 dialog archive carried a false impossibility, unmarked.** The
  in-app agent's reply answered *"DEFINITIVE: No. You cannot wire LoadAudio into
  the ElevenLabs clone node"* and **recommended dropping voice cloning entirely**.
  Cloning works — job `920dc2e0-e420-473a-9cb9-45b84b0fea65` completed, producing
  48 kHz / 3.520 s of speech through that exact path, and the runtime slot is
  `files.audio0`.

  The reply had never been archived at all; only the outbound brief had. It is now
  written to the record with a correction banner, paired with a verification that
  refutes it from measurement, and the studio thread table carries both rounds.
  Preserved rather than deleted: the archive is the record, and removing a wrong
  answer destroys the evidence of how it was wrong.

  Left unmarked, the next session to read it would have dropped a working route.

- The docs contract only modelled `*-brief.md` and `*-verification.md`, so an
  inbound agent reply was an unclassified file escaping every check. `*-reply.md`
  is now a first-class kind with its own rules: it must never name a paste target,
  and **it may never be archived without a paired verification** — an unpaired
  reply reads as fact.

### Added

- Release artifacts (`.whl` + `.tar.gz`) are now attached to the GitHub Release,
  after a successful PyPI upload. PyPI remains the distribution channel; these
  make the Release page self-contained for anyone auditing what a tag produced.
- A test asserting `tools/__init__.py`'s `__version__` matches `pyproject.toml`.
  `release.yml` already failed a publish on a tag mismatch, but nothing caught the
  two files disagreeing with each other — a drifted `__version__` ships silently
  and then misreports itself at runtime.

## [1.0.0] — 2026-08-22

First stable release. The pipeline delivers a finished dub, and the verification
layer that makes that claim checkable is now the shipped product.

### Added

- **`fxdub-dialogue` — the content receipt.** Checks what a take actually *says*
  against an authored scene script, from a word-level diarized transcript: every
  scripted line present and in order, no invented speech, no cross-character
  overlap, no mid-line straggle, one voice per character, fits the clip.
  `--only-speaker` narrows the contract to a single character, which is how a
  per-character stem is verified.
- **Scene scripts** (`docs/scenes/*.json`) — dialogue, cast, clip duration, and
  per-line delivery direction as data. `max_gap_s` carries a director's phrasing
  note with the reason attached.
- **`fxdub.vo_graphs`** — builders for the seven VO-stage ComfyUI graph shapes
  (voice design, same-engine audio reference, clone-and-speak, splice,
  place-on-timeline, mix, transcribe). Pure functions to a `dict`; nothing is
  submitted, uploaded, or spent from this package.
- **Five API-format trap detectors** in `graph_lint`, each proven red against the
  graph that actually failed and silent on the graph that ran.
- Packaged for PyPI with zero runtime dependencies, `py.typed`, and two console
  scripts. Published via Trusted Publishing (OIDC) — no long-lived token exists.
- `SECURITY.md` with a full threat model; `verify.sh` as the single gate
  (test + build + install-smoke); `pip-audit` and an empty-runtime-dependency
  assertion in CI.

### Changed

- **README rewritten.** The previous one described a v0 design with ACE-Step for
  ambience and Chatterbox for dialogue; both were retired during development and
  the pipeline now ships a delivered dub.
- **Ambience is ElevenLabs `eleven_sfx_v2`** (48 kHz, exact duration, loop flag).
  ACE-Step 1.5 is retired from the ambience path — it is a *music* model, and its
  rain bed metered −39.29 LUFS, inaudible under the mix.
- **CLI error handling** — structured `{code, message, hint}` on stderr, exit 1
  for a contract failure and 2 for a runtime error, `--debug` to re-raise.
- Test suite 104 → 167.

### Fixed

- A scene stem could carry lines the script never asked for and pass every check,
  because nothing verified content. Two such takes reached review before
  `fxdub-dialogue` existed.
- `--only-speaker` naming a character absent from the scene passed vacuously — an
  empty contract satisfies every check and renders as success. Now exits 2.

### Measured (v2.8 delivery run)

48 kHz mix at −18.09 LUFS · dialogue +11.17 LU over the bed · 161 frames intact ·
10.069 s · 19/19 container checks · 11/11 content checks.

### Traps recorded

The project trap ledger grew 52 → 65. The load-bearing ones:

- Prompt-designed voices are non-deterministic *regardless of seed* — cast once,
  keep the approved audio, reference or splice it thereafter. Never re-render an
  approved character.
- Cross-engine voice cloning does not preserve identity.
- `ElevenLabsInstantVoiceClone` wants `files.audio0`, not the `files.item_1` its
  schema advertises — and a dry run accepts the wrong name.
- A dry-run pass is not proof of execution; it does not validate dotted
  auto-grow slot names.
- ByteDance `audio reference` mode reproduces the reference clip's dialogue
  content, not just its timbre.
- `pitch_rate` is node-global, so one node cannot voice two characters; its
  timestamps address an absolute output timeline, so per-character passes layer.
- `eleven_v3` inline audio tags work: consumed as direction, not spoken
  (2.240 s → 2.880 s on an identical voice and seed).

## [0.1.0] — 2026-08-21

Scaffold.

- Research-grounded architecture dispatch (5 study-swarm lanes, 45 findings, external citation verification with in-repo Ed25519 receipt): caption-mediated three-layer design (bed / spots / dialogue), deterministic subtractive rewrite stage, dialogue-anchored mix at −18 LUFS / −1 dBTP / 48 kHz, dub-kit deliverable set, governance layer (consent gate, watermark stance, Art. 50 manifest).
- Knowledge Base: every stage's local/cloud × permissive/conditional/paid options with verified licenses and measured credit costs.
- Archived the Comfy Cloud in-app agent's as-built v1 graphs (pulled over the API) with a 10-item defect ledger; demo runs verified from billing (SFX 7.63 gpu-sec, dialogue 6.54 gpu-sec — first end-to-end FL_ChatterboxTTS cloud measurement) and output headers (ACE 1.0 = 44.1 kHz stereo, Chatterbox = 24 kHz mono).
- v2 build brief for the Comfy Agent: ACE-1.5 port, duration coupling, resample/gain-staged mix, loudness manifest, SaveText caption trail, sparse frame sampling, VHS_VideoCombine mux-back.
