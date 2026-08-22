# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
