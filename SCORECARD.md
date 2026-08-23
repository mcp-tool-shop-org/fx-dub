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
