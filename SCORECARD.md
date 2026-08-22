# Scorecard

**Repo:** mcp-tool-shop-org/fx-dub
**Date:** 2026-08-22
**Type tags:** `[all]` `[cli]` `[pypi]`

Scores are the state **at the start of the full treatment**, before remediation.
The post-treatment result is at the bottom and is the actual `shipcheck audit`
output, not an estimate.

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
