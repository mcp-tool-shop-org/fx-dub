"""Container probes for fx-dub receipts — FLAC STREAMINFO and MP4 atoms, stdlib only.

Both readers exist because an fx-dub receipt is a *measurement*, not a report: the
sample rate of a mixed master and the presence of an audio track in a dubbed video
are the two claims most likely to be wrong and least likely to be noticed.

The MP4 reader deliberately reads BOTH the movie header (``mvhd``) and each track
header (``mdhd``). They disagree on real files — the audition fixture has a sane
track and a timescale-0 movie header — and a probe that reads only one of them
will report a confident wrong answer. See ``kb/fxdub.db`` traps.
"""

from __future__ import annotations

import re
import struct

FLAC_MAGIC = b"fLaC"


def parse_streaminfo(data: bytes) -> dict:
    """Decode a FLAC file's STREAMINFO block into its audio parameters."""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("parse_streaminfo expects bytes")
    if data[:4] != FLAC_MAGIC:
        raise ValueError("not a FLAC stream: missing 'fLaC' magic")
    if len(data) < 4 + 4 + 34:
        raise ValueError("truncated FLAC: no room for a STREAMINFO block")

    block_type = data[4] & 0x7F
    if block_type != 0:
        raise ValueError(
            "first metadata block is type {0}, expected STREAMINFO (0)".format(block_type)
        )
    body = data[8:8 + 34]
    packed = int.from_bytes(body[10:18], "big")
    sample_rate = (packed >> 44) & 0xFFFFF
    channels = ((packed >> 41) & 0x7) + 1
    bits_per_sample = ((packed >> 36) & 0x1F) + 1
    total_samples = packed & 0xFFFFFFFFF
    if sample_rate == 0:
        raise ValueError("STREAMINFO declares sample_rate 0 (invalid stream)")
    return {
        "sample_rate": sample_rate,
        "channels": channels,
        "bits_per_sample": bits_per_sample,
        "total_samples": total_samples,
        "duration_s": total_samples / sample_rate,
    }


def probe_mp4(data: bytes) -> dict:
    """Read an MP4's top-level atoms, handler list, and per-track timing.

    Returns ``movie_timescale`` (from ``mvhd``, which real files get wrong) and a
    ``tracks`` list built from ``mdhd``/``hdlr``, plus convenience flags. Never
    raises on a malformed movie header — reports it, because that IS the finding.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("probe_mp4 expects bytes")
    if len(data) < 8:
        raise ValueError("truncated file: no atom header")

    atoms = []
    offset = 0
    while offset < len(data) - 8:
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8].decode("latin1", "replace")
        atoms.append({"type": kind, "size": size})
        if size < 8:
            break
        offset += size
    if not any(a["type"] == "ftyp" for a in atoms):
        raise ValueError("not an MP4/ISO-BMFF file: no 'ftyp' atom")

    movie_timescale = None
    movie_duration = None
    index = data.find(b"mvhd")
    if index > 0:
        version = data[index + 4]
        if version == 0:
            movie_timescale, movie_duration = struct.unpack(">II", data[index + 12:index + 20])
        else:
            movie_timescale = struct.unpack(">I", data[index + 20:index + 24])[0]
            movie_duration = struct.unpack(">Q", data[index + 24:index + 32])[0]

    handlers = [
        data[m.start() + 12:m.start() + 16].decode("latin1", "replace")
        for m in re.finditer(b"hdlr", data)
    ]

    tracks = []
    for match in re.finditer(b"mdhd", data):
        k = match.start()
        version = data[k + 4]
        if version == 0:
            timescale, duration = struct.unpack(">II", data[k + 16:k + 24])
        else:
            timescale = struct.unpack(">I", data[k + 28:k + 32])[0]
            duration = struct.unpack(">Q", data[k + 32:k + 40])[0]
        tracks.append({
            "timescale": timescale,
            "duration": duration,
            "duration_s": (duration / timescale) if timescale else None,
        })

    frame_count = None
    m = re.search(b"stsz", data)
    if m:
        _, frame_count = struct.unpack(">II", data[m.start() + 8:m.start() + 16])

    return {
        "atoms": atoms,
        "movie_timescale": movie_timescale,
        "movie_duration": movie_duration,
        "movie_header_valid": bool(movie_timescale),
        "handlers": handlers,
        "tracks": tracks,
        "has_video_track": "vide" in handlers,
        "has_audio_track": "soun" in handlers,
        "frame_count": frame_count,
    }


def parse_lufs(text: str) -> float:
    """Pull the integrated loudness out of an AudioLoudnessMeter manifest.

    The in-graph meter writes ``Integrated Loudness: -12.32 LUFS`` via SaveText.
    """
    match = re.search(r"Integrated Loudness:\s*(-?\d+(?:\.\d+)?)\s*LUFS", text)
    if not match:
        raise ValueError("no 'Integrated Loudness: <n> LUFS' line in manifest")
    return float(match.group(1))
