# Ship Gate

> No repo is "done" until every applicable line is checked.
> Copy this into your repo root. Check items off per-release.

**Tags:** `[all]` every repo · `[npm]` `[pypi]` `[vsix]` `[desktop]` `[container]` published artifacts · `[mcp]` MCP servers · `[cli]` CLI tools

---

## A. Security Baseline

- [x] `[all]` SECURITY.md exists (report email, supported versions, response timeline)
- [x] `[all]` README includes threat model paragraph (data touched, data NOT touched, permissions required)
- [x] `[all]` No secrets, tokens, or credentials in source or diagnostics output
- [x] `[all]` No telemetry by default — state it explicitly even if obvious

### Default safety posture

- [ ] `[cli|mcp|desktop]` Dangerous actions (kill, delete, restart) require explicit `--allow-*` flag — SKIP: fx-dub performs no destructive action. It reads the files named on the command line and writes one receipt at an explicit `--json` path. There is nothing to kill, delete, or restart.
- [x] `[cli|mcp|desktop]` File operations constrained to known directories — reads are the explicit paths given, plus the documented `filename_prefix` globs inside the named run directory; the only write is the `--json` path the caller chooses
- [ ] `[mcp]` Network egress off by default — SKIP: not an MCP server. Stronger claim holds anyway: the package has no HTTP client and an empty runtime dependency list, asserted by CI.
- [ ] `[mcp]` Stack traces never exposed — structured error results only — SKIP: not an MCP server. Equivalent CLI behaviour is covered on line 28.

## B. Error Handling

- [x] `[all]` Errors follow the Structured Error Shape: `code`, `message`, `hint`, `cause?`, `retryable?` — emitted as JSON on stderr (`scene_not_found`, `words_malformed`, `unknown_speaker`, `receipt_unwritable`, …); covered by `CliContractTests`
- [x] `[cli]` Exit codes: 0 ok · 1 user error · 2 runtime error · 3 partial success — 0 pass, 1 contract failed (a finding, with a receipt to read), 2 the tool could not run. 3 is unused: a receipt is all-or-nothing, there is no partial verification.
- [x] `[cli]` No raw stack traces without `--debug` — input errors return the structured shape; `--debug` re-raises. Asserted by `test_malformed_json_exits_two_without_a_traceback`.
- [ ] `[mcp]` Tool errors return structured results — server never crashes on bad input — SKIP: not an MCP server
- [ ] `[mcp]` State/config corruption degrades gracefully (stale data over crash) — SKIP: not an MCP server; fx-dub holds no state between runs
- [ ] `[desktop]` Errors shown as user-friendly messages — no raw exceptions in UI — SKIP: not a desktop app
- [ ] `[vscode]` Errors surface via VS Code notification API — no silent failures — SKIP: not a VS Code extension

## C. Operator Docs

- [x] `[all]` README is current: what it does, install, usage, supported platforms + runtime versions
- [x] `[all]` CHANGELOG.md (Keep a Changelog format)
- [x] `[all]` LICENSE file present and repo states support status
- [x] `[cli]` `--help` output accurate for all commands and flags — both console scripts verified after install in `verify.sh`
- [ ] `[cli|mcp|desktop]` Logging levels defined: silent / normal / verbose / debug — secrets redacted at all levels — SKIP: fx-dub emits no log stream. Its only stdout is the receipt itself and its only stderr is the structured error; `--debug` controls traceback surfacing. There are no secrets to redact — the tool never reads credentials.
- [ ] `[mcp]` All tools documented with description + parameters — SKIP: not an MCP server
- [ ] `[complex]` HANDBOOK.md: daily ops, warn/critical response, recovery procedures — SKIP: not an operational service. No daemon, no warn/critical states, nothing to recover. The published Starlight handbook covers install, usage and reference instead.

## D. Shipping Hygiene

- [x] `[all]` `verify` script exists (test + build + smoke in one command) — `./verify.sh`; CI runs exactly this
- [x] `[all]` Version in manifest matches git tag — enforced in `release.yml` before publish, which fails the release on a mismatch
- [x] `[all]` Dependency scanning runs in CI (ecosystem-appropriate) — `pip-audit --strict` on the build/test toolchain
- [ ] `[all]` Automated dependency update mechanism exists — SKIP: zero runtime dependencies by design, and CI fails the build if that list ever becomes non-empty. The build/test toolchain resolves latest on every run and is audited each time, so there is no pinned set for a bot to bump.
- [ ] `[npm]` **Every publishable package** passes `npx @mcptoolshop/shipcheck pack` — SKIP: not an npm package. fx-dub publishes to PyPI; the equivalent packaging check is on lines 51-52.
- [x] `[npm]` `engines.node` set · `[pypi]` `python_requires` set — `requires-python = ">=3.10"`, tested on 3.10 and 3.12 in CI
- [x] `[npm]` Lockfile committed · `[pypi]` Clean wheel + sdist build — `python -m build` produces both; `twine check` runs in `release.yml`; the wheel is installed into a throwaway venv and exercised in `verify.sh`
- [ ] `[vsix]` `vsce package` produces clean .vsix with correct metadata — SKIP: not a VS Code extension
- [ ] `[desktop]` Installer/package builds and runs on stated platforms — SKIP: not a desktop app

## E. Identity (soft gate — does not block ship)

- [x] `[all]` Logo in README header — `docs/assets/logo.png`, centred, width 400
- [x] `[all]` Translations (polyglot-mcp, 8 languages) — ja, zh, es, fr, hi, it, pt-BR + English source, with a language nav bar
- [x] `[org]` Landing page (@mcptoolshop/site-theme) — https://mcp-tool-shop-org.github.io/fx-dub/ plus a 6-page Starlight handbook with pagefind search and an /llms.txt entrance
- [x] `[all]` GitHub repo metadata: description, homepage, topics — 10 topics set

---

## Gate Rules

**Hard gate (A–D):** Must pass before any version is tagged or published.
If a section doesn't apply, mark `SKIP:` with justification — don't leave it unchecked.

**Soft gate (E):** Should be done. Product ships without it, but isn't "whole."

**Checking off:**
```
- [x] `[all]` SECURITY.md exists (2026-02-27)
```

**Skipping:**
```
- [x] `[pypi]` Publishing to PyPI via Trusted Publishing (OIDC) — pending publisher registered for `mcp-tool-shop-org/fx-dub`, workflow `release.yml`, environment `release`. No long-lived token exists.
```
