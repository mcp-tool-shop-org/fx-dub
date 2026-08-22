---
title: fx-dub Handbook
description: Verify a generated dub before anyone hears it — container receipts and spoken-content receipts for AI dialogue pipelines.
sidebar:
  order: 0
---

**fx-dub answers one question: is this dub actually usable?**

Not "is it 48 kHz" — you can check that with `ffprobe`. The question that costs
you a review cycle is whether the take says the right words, in the right voices,
without anyone talking over anyone else.

## Why two receipts

A generated take can be flawless by every measurement a container exposes and
still be unusable. Both of the defects that made this tool necessary looked like
this:

| | Take A | Take B |
|---|---|---|
| Sample rate | 48 kHz ✅ | 48 kHz ✅ |
| Duration | 9.840 s ✅ | 9.840 s ✅ |
| Loudness | −18.1 LUFS ✅ | −18.1 LUFS ✅ |
| **Actually** | said a fourth line nobody wrote | held a **1.880 s** silence mid-sentence |

Take A came from a model in `audio reference` mode reproducing its reference
clip's *dialogue*, not just its timbre — a stem meant to carry one character's
lines quietly re-spoke the other's. Mixed under the real take it sounded like two
men talking over each other.

Take B's pause ran straight into the next character's cue.

Neither is visible to duration. Both are trivially visible to a diarized
transcript. That gap is the whole product.

## The two tools

| Tool | Answers |
|---|---|
| [`fxdub-receipt`](./verifying/#the-container-receipt) | Are the masters, the loudness, the ducking depth and the re-muxed video correct? |
| [`fxdub-dialogue`](./verifying/#the-content-receipt) | Did it say the right words, in the right voices, at the right times? |

Both exit non-zero on failure, so they gate a pipeline rather than decorate it.

## Where to go next

- **[Getting Started](./getting-started/)** — install, and read your first receipt
- **[Scene scripts](./scene-scripts/)** — the contract a take is checked against
- **[Verifying a run](./verifying/)** — every check, and what it traces to
- **[Graph builders](./graph-builders/)** — build ComfyUI VO graphs as code
- **[Reference](./reference/)** — CLI flags, exit codes, Python API

## A principle worth stating early

> **A failing check is a finding, not a bug in the tool.**
> Report it. Never tune the threshold to make it green.

Two checks in this project have been *corrected* rather than tuned — both because
they measured the wrong quantity, and the reasoning lives in their docstrings.
That distinction is the difference between a verifier and a rubber stamp.
