# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| < 1.0   | No — pre-release, superseded by 1.0.0 |

## Reporting a Vulnerability

Email: **64996768+mcp-tool-shop@users.noreply.github.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Version affected
- Potential impact

Please report privately first. Do not open a public issue for an unpatched
vulnerability.

### Response timeline

| Action | Target |
|--------|--------|
| Acknowledge report | 48 hours |
| Assess severity | 7 days |
| Release fix | 30 days |

## Threat model

**The `fx-dub` package runs locally and makes no network calls of any kind.**

| | |
|---|---|
| **Data touched** | Only the files you name on the command line: FLAC/MP4 masters, `*_lufs*.txt` manifests, caption text, and diarized-transcript JSON. Written output is the receipt JSON at the `--json` path you choose. |
| **Data NOT touched** | No credentials, no API keys, no environment secrets, no config outside the paths you pass, no other files in the run directory beyond the documented glob patterns. |
| **Permissions required** | Filesystem read on the inputs; filesystem write only if you pass `--json`. Nothing else. |
| **Network egress** | **None.** There is no HTTP client in this package and no dependency that could add one — the dependency list is empty by design. |
| **Telemetry** | **None.** Nothing is collected, counted, or transmitted. There is no opt-out because there is nothing to opt out of. |
| **Credentials** | Never read, stored, or transmitted. |

### The one thing worth understanding

`fxdub.vo_graphs` **builds** ComfyUI API-format graph dictionaries. It does not
submit them, and it holds no client, no endpoint, and no token. Building a graph
is a pure function from arguments to a `dict`. Submitting one — and therefore
any spend, any upload, and any egress — is entirely the caller's action through
their own separately-authenticated tooling.

This split is deliberate: it means the package can be run against untrusted
inputs, in CI, or on an air-gapped machine, and the worst it can do is write a
receipt saying the audio failed its contract.

### Parsers and untrusted input

`fxdub.media_probe` parses FLAC `STREAMINFO` blocks and MP4 atom headers with
the standard library rather than shelling out to `ffprobe`. That is a smaller
attack surface than invoking an external binary, but it is still binary parsing:

- Parsers are **read-only** and bounded — they read headers, never execute,
  never allocate based on an unvalidated length field without a bound.
- Malformed input yields a failed check, not a crash: `check_run` is documented
  to never raise on a bad artifact, and the suite asserts this against
  deliberately corrupt fixtures.
- If you find an input that causes an unhandled exception, a hang, or memory
  growth, that is a bug worth reporting under the process above.

### Generated media and disclosure

fx-dub verifies dubs produced by third-party speech models. It does not
generate speech itself, and it takes no position on the licence of the audio you
feed it. Two responsibilities stay with you:

- **Consent.** Do not clone a real person's voice without their permission.
  The repository's Knowledge Base documents the consent stance in full.
- **Disclosure.** Synthetic speech published in the EU carries an Article 50
  machine-readable-marking obligation. The receipt JSON is designed to serve as
  part of that provenance trail, but emitting it is not by itself compliance.

## Scope

In scope: the `fx-dub` Python package and its verifiers.

Out of scope: the ComfyUI nodes, cloud platform, and speech models the pipeline
talks to — report those to their respective maintainers. Model weights carry
their own licences and their own risks; the repository's Knowledge Base maps
them honestly.
