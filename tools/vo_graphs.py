#!/usr/bin/env python3
"""Builders for the fx-dub VO-stage graphs, in Comfy Cloud API format.

WHY THIS MODULE EXISTS (2026-08-22, session 4)
----------------------------------------------
``HANDOFF.md`` §4 records that v2.3-v2.7 "exist only in the session transcript
and in ``runs/``" because they were hand-authored API JSON typed into a chat.
Session 4 then repeated that mistake about fifteen more times in one sitting:
every render, splice and mix was a one-off blob that vanished with the session.

A graph you cannot rebuild is not a pipeline stage, it is an anecdote. These
builders are the durable form: each returns an API-format dict, each is covered
by tests, and each is linted by ``graph_lint.API_DETECTORS`` so the traps that
cost real jobs cannot be re-authored by hand.

Every builder returns ``{node_id: {"class_type": .., "inputs": {..}}}`` ready for
``submit_workflow``. None of them submit anything — building is free and
testable; spending is the caller's decision.

Cloud audio is addressed by STORAGE KEY: any ``SaveAudioAdvanced`` output can be
reloaded by its content hash through ``LoadAudio``, whose COMBO never lists it.
That is what makes re-mixing free and deterministic.
"""

from __future__ import annotations

#: ElevenLabs is the only 48 kHz-native TTS on the platform; every local engine
#: decodes 24 kHz mono. ByteDance can be asked for 48 kHz explicitly.
RUNTIME_SAMPLE_RATE = 48000

#: The runtime slot name for the clone node's auto-grow file list. NOT the
#: ``files.item_1`` that ``get_node`` advertises -- see the trap in kb/fxdub.db.
CLONE_SLOT = "files.audio0"


def _save(node_id, src, prefix, fmt="flac"):
    return {node_id: {"class_type": "SaveAudioAdvanced",
                      "inputs": {"audio": src, "filename_prefix": prefix, "format": fmt}}}


def load_audio(node_id, storage_key):
    """A cloud asset by content hash. The COMBO does not list it; it resolves anyway."""
    return {node_id: {"class_type": "LoadAudio", "inputs": {"audio": storage_key}}}


def bytedance_text_only(prompt, prefix, pitch_rate=0, seed=1, speech_rate=0,
                        sample_rate=RUNTIME_SAMPLE_RATE):
    """Voice DESIGN from a written brief. Use for CASTING only.

    Output identity is non-deterministic regardless of seed, so a voice produced
    here cannot be recalled by re-running. Once a take is approved, keep the
    AUDIO and reference or splice it -- never re-render the character.

    ``pitch_rate`` is node-global: it shifts every speaker in the prompt, so give
    each character its own pass. Timestamps (``[2.3s:4.0s] line``) address an
    ABSOLUTE output timeline and the leading silence is written for you, so
    per-character passes layer without alignment work.
    """
    graph = {"1": {"class_type": "ByteDanceSeedAudio", "inputs": {
        "text_prompt": prompt,
        "reference_mode": "text only",
        "sample_rate": str(sample_rate),
        "speech_rate": speech_rate,
        "loudness_rate": 0,
        "pitch_rate": pitch_rate,
        "seed": seed,
        "model": "seed-audio-1.0-multilingual",
    }}}
    graph.update(_save("2", ["1", 0], prefix))
    return graph


def bytedance_audio_reference(reference_key, prompt, prefix, pitch_rate=0, seed=1,
                              sample_rate=RUNTIME_SAMPLE_RATE):
    """Same-engine voice reference. Holds identity where cross-engine cloning did not.

    WARNING: this mode reproduces the reference clip's DIALOGUE CONTENT, not just
    its timbre. A multi-line reference makes the model re-speak lines the prompt
    never asked for. Use a single-speaker reference and gate the output with
    ``tools/dialogue_receipt.py --only-speaker``.
    """
    graph = {}
    graph.update(load_audio("1", reference_key))
    graph["2"] = {"class_type": "ByteDanceSeedAudio", "inputs": {
        "text_prompt": prompt,
        "reference_mode": "audio reference",
        "reference_mode.reference_audio_1": ["1", 0],
        "sample_rate": str(sample_rate),
        "speech_rate": 0,
        "loudness_rate": 0,
        "pitch_rate": pitch_rate,
        "seed": seed,
        "model": "seed-audio-1.0-multilingual",
    }}
    graph.update(_save("3", ["2", 0], prefix))
    return graph


def elevenlabs_clone_tts(reference_key, text, prefix, stability=0.5, speed=1.0,
                         similarity_boost=0.75, seed=1):
    """Clone a voice from a cloud asset, then speak ``text`` in it.

    The reference reaches the clone node through ``files.audio0``. Cross-ENGINE
    cloning (e.g. a ByteDance take into ElevenLabs) does not preserve identity;
    ElevenLabs' guidance wants real speech, and short synthetic references come
    back approximated.
    """
    graph = {}
    graph.update(load_audio("1", reference_key))
    graph["2"] = {"class_type": "ElevenLabsInstantVoiceClone",
                  "inputs": {CLONE_SLOT: ["1", 0], "remove_background_noise": False}}
    graph["3"] = {"class_type": "ElevenLabsTextToSpeech", "inputs": {
        "voice": ["2", 0],
        "text": text,
        "stability": stability,
        "apply_text_normalization": "auto",
        "model": "eleven_v3",
        "model.speed": speed,
        "model.similarity_boost": similarity_boost,
        "language_code": "en",
        "seed": seed,
        "output_format": "opus_48000_192",
    }}
    graph.update(_save("4", ["3", 0], prefix))
    return graph


def splice(storage_key, keep_spans, prefix):
    """Keep only ``keep_spans`` of a clip, butt-joined in order.

    ``keep_spans`` is [(start_s, duration_s), ...]. This is how an approved take
    is repaired without regenerating it -- the fix for a mid-line pause that runs
    into the next character's cue. The voice is bit-identical to the approved
    audio because nothing passes through a model.

    ``AudioPad`` is NOT used: it raises ``UnboundLocalError: pad_samples`` on
    Comfy Cloud for every input. ``AudioConcat`` is the working primitive.
    """
    if not keep_spans:
        raise ValueError("keep_spans must not be empty")
    graph = {}
    graph.update(load_audio("1", storage_key))
    tails = []
    for i, (start, duration) in enumerate(keep_spans):
        node_id = str(10 + i)
        graph[node_id] = {"class_type": "TrimAudioDuration",
                          "inputs": {"audio": ["1", 0],
                                     "start_index": float(start),
                                     "duration": float(duration)}}
        tails.append([node_id, 0])
    joined = tails[0]
    for i, nxt in enumerate(tails[1:]):
        node_id = str(50 + i)
        graph[node_id] = {"class_type": "AudioConcat",
                          "inputs": {"audio1": joined, "audio2": nxt, "direction": "after"}}
        joined = [node_id, 0]
    graph.update(_save("90", joined, prefix))
    return graph


def place(storage_key, at_seconds, prefix, sample_rate=RUNTIME_SAMPLE_RATE, channels=2):
    """Put a clip on a timeline at ``at_seconds`` by prefixing generated silence."""
    graph = {}
    graph["1"] = {"class_type": "EmptyAudio",
                  "inputs": {"duration": float(at_seconds),
                             "sample_rate": sample_rate, "channels": channels}}
    graph.update(load_audio("2", storage_key))
    graph["3"] = {"class_type": "AudioConcat",
                  "inputs": {"audio1": ["1", 0], "audio2": ["2", 0], "direction": "after"}}
    graph.update(_save("4", ["3", 0], prefix))
    return graph


def mix(key_a, key_b, prefix, gain_a_db=0.0, gain_b_db=0.0):
    """Overlay two tracks. ``key_a`` goes on ``audio_1``, whose sample rate and
    (longer) duration the mix adopts -- there is no rate converter on cloud, so
    input order is the only lever."""
    graph = {}
    graph.update(load_audio("1", key_a))
    graph.update(load_audio("2", key_b))
    graph["3"] = {"class_type": "AudioMix",
                  "inputs": {"audio_1": ["1", 0], "audio_2": ["2", 0],
                             "gain_1_db": gain_a_db, "gain_2_db": gain_b_db}}
    graph.update(_save("4", ["3", 0], prefix))
    return graph


def transcribe(storage_key, prefix):
    """Word-level diarized transcript -- the input to ``dialogue_receipt.py``.

    ``num_speakers`` MUST be 0 when diarizing (the node rejects both together),
    and ``diarization_threshold`` caps at 0.4. Output slot 2 is the word list.
    """
    graph = {}
    graph.update(load_audio("1", storage_key))
    graph["2"] = {"class_type": "ElevenLabsSpeechToText", "inputs": {
        "audio": ["1", 0],
        "model": "scribe_v2",
        "model.tag_audio_events": False,
        "model.diarize": True,
        "model.diarization_threshold": 0.22,
        "model.temperature": 0,
        "model.timestamps_granularity": "word",
        "language_code": "en",
        "num_speakers": 0,
        "seed": 1,
    }}
    graph["3"] = {"class_type": "SaveText",
                  "inputs": {"text": ["2", 2], "filename_prefix": prefix, "format": "json"}}
    return graph


def gap_closing_spans(words, after_index, lead_in=0.1, tail=0.08, head=0.06):
    """Spans that excise the silence following ``words[after_index]``.

    Given a diarized word list and the index of the word before the offending
    gap, return ``[(start, duration), ...]`` for :func:`splice` that keeps the
    speech and drops the dead air, leaving ``tail + head`` seconds of join.
    """
    if after_index < 0 or after_index + 1 >= len(words):
        raise ValueError("after_index must name a word with a successor")
    first_start = max(0.0, words[0]["start"] - lead_in)
    cut_at = words[after_index]["end"] + tail
    resume = max(cut_at, words[after_index + 1]["start"] - head)
    last_end = words[-1]["end"] + tail
    return [
        (round(first_start, 3), round(cut_at - first_start, 3)),
        (round(resume, 3), round(last_end - resume, 3)),
    ]
