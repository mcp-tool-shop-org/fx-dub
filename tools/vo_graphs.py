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


# --- picture stage (2026-08-23, session 5: lip-sync in post) ----------------------
#
# These four exist for the same reason the audio builders above do. Session 5
# hand-typed every lip-sync graph into a chat window -- the exact mistake this
# module's docstring was written to stop -- and only noticed after the paid run.

def load_video(node_id, storage_key):
    """A cloud VIDEO asset by content hash. Like LoadAudio, the COMBO never lists it.

    Proven by execution 2026-08-23 (job aba137d3-...): no upload step exists or
    is needed.
    """
    return {node_id: {"class_type": "LoadVideo", "inputs": {"file": storage_key}}}


def _save_video(node_id, src, prefix):
    """SaveVideo WITHOUT ``codec.encoding``.

    Sending ``codec.encoding`` returns ``candidate.toLowerCase is not a function``
    from local pre-flight and no verdict at all: its options are objects
    (``{"key": "auto", ...}``), not strings, and the validator lowercases them.
    Omitting the field validates clean and preserves the stream.
    """
    return {node_id: {"class_type": "SaveVideo",
                      "inputs": {"video": src, "filename_prefix": prefix,
                                 "format": "mp4", "codec": "h264"}}}


def place_exact(storage_key, at_seconds, clip_seconds, total_seconds, prefix,
                sample_rate=RUNTIME_SAMPLE_RATE, channels=2):
    """``place`` plus a tail, so the result is EXACTLY ``total_seconds`` long.

    Prefer this over :func:`place` whenever the track drives a lip-sync node.
    ``SyncLipSyncNode``'s ``sync_mode: silence`` pads the shorter track but the
    schema never says at which END, and the only way to find out is a
    full-duration paid run. Matching the picture duration exactly leaves nothing
    to pad and makes the question moot for free (measured 2026-08-23: 483000
    samples / 48 kHz = 10.0625 s, delta 0.0000 s against the picture).

    ``clip_seconds`` must be MEASURED from the cloud artifact, not assumed from a
    local file of the same name -- session 5 asserted a cloud key carried leading
    silence on the strength of a local 4.032 s file when the key itself decodes to
    1.415 s, which would have put the mouth 2.3 s early on a paid run.
    """
    lead = float(at_seconds)
    tail = float(total_seconds) - lead - float(clip_seconds)
    if tail < 0:
        raise ValueError(
            "clip does not fit: {0}s at {1}s exceeds a {2}s timeline".format(
                clip_seconds, at_seconds, total_seconds))
    graph = {}
    graph["1"] = {"class_type": "EmptyAudio",
                  "inputs": {"duration": lead, "sample_rate": sample_rate,
                             "channels": channels}}
    graph.update(load_audio("2", storage_key))
    graph["3"] = {"class_type": "AudioConcat",
                  "inputs": {"audio1": ["1", 0], "audio2": ["2", 0], "direction": "after"}}
    graph["4"] = {"class_type": "EmptyAudio",
                  "inputs": {"duration": round(tail, 6), "sample_rate": sample_rate,
                             "channels": channels}}
    graph["5"] = {"class_type": "AudioConcat",
                  "inputs": {"audio1": ["3", 0], "audio2": ["4", 0], "direction": "after"}}
    graph.update(_save("6", ["5", 0], prefix))
    return graph


def lipsync(video_key, audio_key, prefix, speaker_x, speaker_y, speaker_frame=0,
            sync_mode="silence", seed=42):
    """sync.so re-sync of one named face, driven by a per-character track.

    ``speaker_selection`` is pinned to ``coordinates`` and is NOT optional. Its
    default is ``default`` ("let the model decide"), which returns a completed,
    correctly-framed, well-synced MP4 with SOMEONE ELSE's mouth moving and passes
    every container check we own. Pass the coordinates of the character whose
    track this is.

    ``sync_mode`` defaults to ``silence``: bounce/loop/remap all resize the output
    to the AUDIO length (remap time-stretches the picture) and cut_off trims to the
    shorter track. Only silence leaves the picture's duration alone.

    NOTE the output is re-timed: a 161-frame / 16 fps source returns ~473 frames at
    ~47 fps over the same duration. Duration and resolution survive; frame count
    does not. Do not assert frame-count preservation on the result.
    """
    graph = {}
    graph.update(load_video("1", video_key))
    graph.update(load_audio("2", audio_key))
    graph["3"] = {"class_type": "SyncLipSyncNode",
                  "inputs": {"video": ["1", 0], "audio": ["2", 0], "seed": int(seed),
                             "model": "sync-3",
                             "model.sync_mode": sync_mode,
                             "model.speaker_selection": "coordinates",
                             "model.speaker_frame": int(speaker_frame),
                             "model.speaker_x": int(speaker_x),
                             "model.speaker_y": int(speaker_y)}}
    graph.update(_save_video("4", ["3", 0], prefix))
    return graph


def mux(video_key, audio_key, prefix):
    """Lay an audio track over a VIDEO by way of its decoded frames.

    ``AudioVideoCombine`` would be the obvious node and it is BROKEN on Comfy
    Cloud -- ``ImportError: TorchCodec is required for save_with_torchcodec``
    (measured 2026-08-23, job 3397f3e9-...). ``VHS_VideoCombine`` takes images
    plus an optional audio track and works.

    ``frame_rate`` is driven by the LINK from ``GetVideoComponents``, never a bare
    widget: the widget underneath a live link reads 8, and cutting the link turns
    a 10 s dub into a 20 s one silently. Taking the rate from the same node that
    produced the frames also keeps the two self-consistent.
    """
    graph = {}
    graph.update(load_video("1", video_key))
    graph["2"] = {"class_type": "GetVideoComponents", "inputs": {"video": ["1", 0]}}
    graph.update(load_audio("3", audio_key))
    graph["4"] = {"class_type": "VHS_VideoCombine",
                  "inputs": {"images": ["2", 0],
                             "frame_rate": ["2", 2],
                             "loop_count": 0,
                             "filename_prefix": prefix,
                             "format": "video/h264-mp4",
                             "pingpong": False,
                             "save_output": True,
                             "audio": ["3", 0]}}
    return graph


def frames(video_key, prefix, indices):
    """Decode-only frame extract -- free, and the only way to read a named frame.

    ``ImageFromBatch`` CLAMPS an out-of-range ``batch_index`` to the last frame
    instead of erroring, and ``GetVideoComponents`` decodes at the SOURCE rate
    (161 frames at 16 fps) even from a 473-frame container. Cross-check the
    returned images by content hash before trusting that you got the frame you
    asked for.
    """
    graph = {}
    graph.update(load_video("1", video_key))
    graph["2"] = {"class_type": "GetVideoComponents", "inputs": {"video": ["1", 0]}}
    node = 3
    for idx in indices:
        graph[str(node)] = {"class_type": "ImageFromBatch",
                            "inputs": {"image": ["2", 0], "batch_index": int(idx), "length": 1}}
        graph[str(node + 1)] = {"class_type": "SaveImage",
                                "inputs": {"images": [str(node), 0],
                                           "filename_prefix": "{0}/f{1:03d}".format(prefix, int(idx))}}
        node += 2
    return graph


#: AudioMix's per-track gains are clamped to -24..+6 dB. Anything outside that
#: needs AudioAdjustVolume in front, which is why the delivered mix's "VO +7 dB"
#: could never have come from AudioMix (measured 2026-08-23: submitting
#: gain_2_db=7.0 returns value_bigger_than_max, max 6.0).
AUDIOMIX_GAIN_MIN_DB = -24.0
AUDIOMIX_GAIN_MAX_DB = 6.0


def mix_dialogue_anchored(bed_key, vo_key, prefix, vo_gain_db=7, bed_gain_db=-12.0):
    """The delivered mix shape: bed on ``audio_1``, VO boosted ahead of the bus.

    The bed goes on ``audio_1`` because AudioMix adopts that track's sample rate
    and the longer duration, and the bed is the full-length 48 kHz one.

    ``vo_gain_db`` is applied by ``AudioAdjustVolume`` rather than by the bus,
    because the bus clamps at +6 dB and the delivered run used +7. Gain-stage from
    a meter, never from a remembered number: two engines measured 6.7 dB apart on
    the same line.
    """
    if not AUDIOMIX_GAIN_MIN_DB <= bed_gain_db <= AUDIOMIX_GAIN_MAX_DB:
        raise ValueError(
            "bed_gain_db {0} is outside AudioMix's {1}..{2} dB range; put it "
            "through AudioAdjustVolume instead".format(
                bed_gain_db, AUDIOMIX_GAIN_MIN_DB, AUDIOMIX_GAIN_MAX_DB))
    graph = {}
    graph.update(load_audio("1", bed_key))
    graph.update(load_audio("2", vo_key))
    graph["3"] = {"class_type": "AudioAdjustVolume",
                  "inputs": {"audio": ["2", 0], "volume": int(vo_gain_db)}}
    graph["4"] = {"class_type": "AudioMix",
                  "inputs": {"audio_1": ["1", 0], "audio_2": ["3", 0],
                             "gain_1_db": bed_gain_db, "gain_2_db": 0.0}}
    graph.update(_save("5", ["4", 0], prefix))
    return graph
