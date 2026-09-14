# Scorecard

**Repo:** mcp-tool-shop-org/fx-dub
**Assessed:** 2026-08-22 (v0.x → v1.0.0) · **re-audited:** 2026-08-23 (v1.1.0)
**Type tags:** `[all]` `[cli]` `[pypi]`

Scores are the state **at the start of the full treatment**, before remediation —
they describe v1.0.0's starting position and are kept as evidence, not refreshed.
The post-treatment result is below, and the v1.1.0 re-audit is at the bottom. Both
are actual `shipcheck audit` output, not estimates.

## Pre-Remediation Assessment

| Category | Score | Notes |
|----------|-------|-------|
| A. Security | 3/10 | No `SECURITY.md`. No threat model anywhere. The claims that mattered — no network egress, no telemetry, no credential access — were true but undocumented, so a user had no way to know them. |
| B. Error Handling | 2/10 | A missing input file produced a raw traceback. Exit codes were 0/1 only, so "the audio failed its contract" and "the tool could not run" were indistinguishable in CI. No structured error shape. |
| C. Operator Docs | 3/10 | README described a **v0 design** for a pipeline that had since shipped: ACE-Step for ambience and Chatterbox for dialogue, both retired during development; a status table listing a brief as "awaiting relay" that had been answered days earlier; a cost table for a pipeline that no longer existed. CHANGELOG stopped at the scaffold. |
| D. Shipping Hygiene | 2/10 | Not packaged at all — no `pyproject.toml`, no version, nothing installable. No verify script. No dependency scanning. CI ran the test suite and nothing else. |
| E. Identity (soft) | 2/10 | Logo present in the README; no landing page, no handbook, no translations, no GitHub metadata (empty description, empty homepage, zero topics). |
| **Overall** | **12/50** | A repo with a genuinely good verification core and almost no shippable surface around it. |

## Key Gaps

1. **Not installable.** The most valuable thing in the repo — two verifiers that
   catch defects container metrics cannot see — could only be used by cloning it.
2. **The README described software that no longer existed.** Two of the three
   named models had been retired mid-development. The front door actively misled.
3. **Error handling failed the CI contract.** Exit 1 for both a contract failure
   and a bad path means a pipeline cannot tell "look at the audio" from "fix your
   invocation," and a traceback is not an error message.
4. **No security documentation for a tool whose main safety property is a
   negative** — no network, no telemetry, no credentials. Unstated, that is worth
   nothing to a user evaluating it.
5. **No verify gate.** Nothing ran the build, and nothing proved the built
   artifact worked after installation.

## Remediation Priority

1. Package for PyPI + Trusted Publishing; add `verify.sh` as the single gate and
   run it in CI. *(D)*
2. Rewrite the README against what actually ships; add the threat model. *(A, C)*
3. Structured errors, distinct exit codes, `--debug`. *(B)*
4. Landing page, handbook, translations, metadata, `llms.txt`. *(E)*

## Post-Remediation Result

`npx @mcptoolshop/shipcheck audit` — **all hard gates pass**:

```
Checked:   23
Unchecked: 0
Skipped:   14
Pass rate: 100%
```

| Category | After |
|----------|-------|
| A. Security | `SECURITY.md` with a full threat model; README threat-model section; zero runtime dependencies **asserted by CI** so the no-egress claim cannot silently rot. |
| B. Error Handling | `{code, message, hint}` on stderr; exit 0 / 1 / 2 with 1 and 2 deliberately distinct; `--debug` to re-raise. Seven CLI-contract tests, including one asserting no traceback leaks. |
| C. Operator Docs | README rewritten against the delivered pipeline; Keep-a-Changelog v1.0.0 entry; 6-page Starlight handbook; `--help` verified post-install in `verify.sh`. |
| D. Shipping Hygiene | `pyproject.toml`, wheel + sdist, `twine check`, `python_requires >=3.10`, tag/version equality enforced at publish, `pip-audit --strict` in CI, `./verify.sh` as the one gate. |
| E. Identity | Landing page, handbook with pagefind search, `/llms.txt` entrance, 8 languages, 10 GitHub topics, description + homepage. |

The 14 skips are all genuine type mismatches — `[npm]`, `[mcp]`, `[desktop]`,
`[vsix]`, `[vscode]` items on a Python CLI — plus three reasoned ones: no
destructive actions to gate, no log stream to level, and no dependency-update bot
for a package with zero runtime dependencies. Each carries its reasoning inline in
`SHIP_GATE.md`.

---

## v1.1.0 Re-Audit — 2026-08-23

`npx @mcptoolshop/shipcheck audit` — **all hard gates pass**, unchanged:

```
Checked:   23
Unchecked: 0
Skipped:   14
Pass rate: 100%
```

**That number reads this repo's `SHIP_GATE.md` checkboxes, not the repo.** So the
release's hard-gate claims were re-verified independently, against the **published
wheel** rather than the working tree:

| Gate | Claim | How it was confirmed |
|---|---|---|
| A | No network egress | no `requests` / `urllib` / `http` / `socket` import anywhere in `tools/` |
| A | Reads and writes constrained | every `open(..., "w")` grepped: two, both the caller's `--json` path |
| B | Structured errors, distinct exit codes | `{code, message, hint}` on stderr; **2** missing dir · **1** contract failed · **0** clean |
| C | `--help` accurate | `--scene` present and described in the generated help |
| D | Version matches tag | `pyproject` `1.1.0` = tag `v1.1.0` |
| D | Zero runtime dependencies | `dependencies = []`, now asserted locally as well as in CI |
| D | Clean packaging | wheel carries 6 modules + `py.typed` + LICENSE, nothing stray |

### What the walk found

A 100% pass rate is a self-report, and one item had rotted:

- **`scene_unreadable` shipped in v1.1.0 with no test coverage**, while gate B
  already claimed its error codes were covered. The behaviour was correct — the
  assertion simply did not exist. Closed by `SceneFlagContractTests` (5 tests:
  missing scene, malformed scene, `--debug` re-raise, the check appearing with
  `--scene`, and its absence without).
- **The zero-dependency promise was enforced only in CI.** `./verify.sh` is
  documented as the single local gate, so a change adding a dependency would pass
  locally and fail in CI. Closed by `ZeroDependencyTests`, which is itself proven
  able to go red.

Suite: **189 → 197 tests**, `verify.sh` PASS.

### The 14 skips, re-walked

Thirteen are type mismatches — `[npm]`, `[mcp]`, `[desktop]`, `[vsix]`, `[vscode]`
items on a Python CLI — and stay true until fx-dub becomes one of those things.
The three behavioural ones were re-checked mechanically rather than carried
forward on trust; the method for each is recorded in `SHIP_GATE.md` so the next
release can repeat it instead of re-deriving it.

---

## v1.2.0 re-audit — 2026-09-14

`npx @mcptoolshop/shipcheck audit` → **23 checked / 0 unchecked / 14 skipped,
100%, all hard gates pass.** Actual output, not an estimate.

### What the walk found

The audit was green and **two real defects were sitting behind it**, both shipping
since v1.0.0. Neither is a shipcheck gap in the sense of a missed checkbox — they
are defects whose only symptom is extra *success*, which is the class no
checkbox-shaped gate can see.

- **A committed receipt carried the operator's absolute path.** The Phase-0
  identity scan halted on `runs/2026-08-22-audition-01/receipt.json`, which
  recorded its `run_dir` as the full session temp path — home directory, username,
  session UUID — in a public repo. Published artifacts were never affected
  (`runs/` is in neither the sdist nor the wheel; both re-scanned to confirm).

  Gate A3 covers secrets and tokens. It does not cover operator identity, and the
  identity scan is a **separate hard gate of the same class** — it must run at
  Phase 0, again before the Phase-6 push, and against the leaving artifact.

  Root cause was `audition_receipt.check_run()` recording whatever absolute path it
  was handed, so scrubbing the file alone would have re-leaked on the next run.
  Closed by `_run_label()` plus `tests/test_no_local_paths.py` (12 tests), which
  scans every git-tracked file and the generator itself, and is **proven red
  against the actual leaked bytes recovered from git history.**

- **CI ran the full matrix twice per commit, and the commit that fixed it did
  not.** Measured by grouping run history by head SHA: five duplicate pairs, four
  of them branch-push + tag-push — every release paid twice. Closed at the trigger
  (`on.push.branches: [main]`) plus `tests/test_workflows.py` (11 tests), proven
  red against the real pre-fix workflow.

### Gate E (identity), re-walked

| | | |
|---|---|---|
| Logo | ✅ | brand repo, unchanged |
| Translations | ✅ | 7 languages, regenerated **before** the tag |
| Landing page | ✅ | builds, pagefind index present |
| Handbook | ✅ | **6 → 7 pages** — added *The Public API* |
| GitHub metadata | ✅ | description, homepage, **11 topics** (+`audiobook`) |

Suite: **197 → 277 tests**, `verify.sh` PASS, identity scan `RESULT CLEAN`.

**The lesson worth carrying:** a 100% pass rate was true and insufficient. Both
defects produced *more* successful output than a healthy repo — a saved receipt,
two green checks — so every alarm surface read normal. Verify by measuring the
artifact, never by reading the config.
