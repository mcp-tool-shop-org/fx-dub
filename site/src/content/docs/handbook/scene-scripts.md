---
title: Scene scripts
description: The contract a take is checked against — dialogue, cast, timing, and direction as data.
sidebar:
  order: 2
---

A scene script is the contract. It holds what your characters say, who says it,
how long the picture is, and — importantly — **the direction that justifies every
threshold**.

```json title="docs/scenes/night-street.json"
{
  "name": "night-street",
  "note": "The Director's staging, verbatim. Do not rewrite the lines.",
  "clip_duration_s": 10.062,
  "max_gap_within_line_s": 0.5,
  "cast": {
    "VOICE": "off-frame, deep and gritty",
    "MAC": "on-frame, gritty, weary"
  },
  "lines": [
    { "speaker": "VOICE", "text": "Hey, how's it going?" },
    { "speaker": "MAC",   "text": "Not bad. Can't complain.",
      "max_gap_s": 0.15,
      "direction": "There's no pause in between. A gap here runs into VOICE's next cue." },
    { "speaker": "VOICE", "text": "Good to hear, good to hear." },
    { "speaker": "VOICE", "text": "Hey, tell Charlie I got that thing for him, whenever he wants to drop by." }
  ]
}
```

## Fields

### Scene level

| Field | Meaning |
|---|---|
| `clip_duration_s` | The picture's length. Speech must end before it. |
| `max_gap_within_line_s` | Default budget for a silence *inside* one line. Defaults to `0.5`. |
| `min_gap_between_speakers_s` | Minimum silence between turns. Defaults to `0.0`. |
| `cast` | Free-form notes per character. Documentation, not checked. |
| `lines` | The ordered dialogue. |

### Line level

| Field | Meaning |
|---|---|
| `speaker` | Character name. **Case-sensitive** — `--only-speaker mac` will not match `MAC`. |
| `text` | What they say. Compared with punctuation and case stripped. |
| `max_gap_s` | Overrides the scene default for *this line only*. |
| `direction` | Why that override exists. Never checked; always read. |

## Why the default is loose and the override is tight

The scene default is `0.5 s` on purpose. A comma pause inside a line is normal
delivery, not a defect, and a verifier that flags every one of them is noise
people learn to ignore.

Where a director has *specified* the phrasing — "there's no pause in between" —
that is a fact about this line, not a global policy. It belongs on the line:

```json
{ "speaker": "MAC", "text": "Not bad. Can't complain.",
  "max_gap_s": 0.15,
  "direction": "There's no pause in between. A gap here runs into VOICE's next cue." }
```

Now the verifier rejects a take that a global threshold would wave through, and
six months from now the `direction` field explains why `0.15` and not `0.4`.

:::tip[Direction belongs in the script]
The alternative is direction living in a chat transcript or someone's head, where
the next render cannot see it. A note in the scene file is the only version that
survives the session that produced it.
:::

## Text matching

Words are compared with punctuation and case removed, apostrophes kept:

- `"Not bad. Can't complain."` matches a transcript of `not bad can't complain`
- A comma where the model produced a full stop is **not** a content defect
- A missing or extra *word* is

This matters because your TTS engine chooses its own punctuation and your ASR
guesses at it. Neither is the thing you are verifying.

## Checking one character at a time

```bash
fxdub-dialogue scene.json voice-stem-words.json --only-speaker VOICE
```

This narrows the contract to VOICE's three lines. Any other speech in that stem
now fails `no_invented_speech`, because a per-character stem is supposed to
contain that character and silence.

A misspelled or absent speaker name exits **2**, not 0 — an empty contract passes
every check vacuously, which is the most dangerous possible result:

```console
$ fxdub-dialogue scene.json words.json --only-speaker NARRATOR
{
  "error": {
    "code": "unknown_speaker",
    "message": "No line in scene.json is spoken by 'NARRATOR'.",
    "hint": "Cast in this scene: MAC, VOICE. Speaker names are case-sensitive."
  }
}
```
