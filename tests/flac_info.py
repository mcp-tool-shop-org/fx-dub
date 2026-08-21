"""flac_info — decode a FLAC STREAMINFO block into a receipt.

The house rule for cloud audio is "verify, don't relay": a downloaded master is
only a measurement once its header has been decoded locally. Both class-A audio
runs in ``kb/fxdub.db`` (the ACE-Step SFX demo at 44.1 kHz stereo and the
ChatterBox dialogue demo at 24 kHz mono) were closed this way, and the open
mix-bus sample-rate question will be closed the same way at audition.

FLAC layout, from the top of the file::

    offset 0   4 bytes   'fLaC' magic
    offset 4   1 byte    metadata block header: bit 7 = last-block flag,
                         bits 6..0 = block type (0 = STREAMINFO, and STREAMINFO
                         is required to be the FIRST block)
    offset 5   3 bytes   big-endian length of the block body (34 for STREAMINFO)
    offset 8   34 bytes  STREAMINFO body:
                 +0   uint16  min block size
                 +2   uint16  max block size
                 +4   uint24  min frame size
                 +7   uint24  max frame size
                 +10  8 bytes packed big-endian:
                          bits 63..44  sample rate      (20 bits)
                          bits 43..41  channels - 1     (3 bits)
                          bits 40..36  bits/sample - 1  (5 bits)
                          bits 35..0   total samples    (36 bits)
                 +18  16 bytes MD5 of the unencoded audio
"""

from __future__ import annotations

import struct

FLAC_MAGIC = b"fLaC"
STREAMINFO_TYPE = 0
STREAMINFO_SIZE = 34
_HEADER_SIZE = len(FLAC_MAGIC) + 4  # magic + block header


def parse_streaminfo(data):
    """Decode the first STREAMINFO block of ``data``.

    :param data: raw bytes from the start of a FLAC file (the first 42 bytes are
        enough; anything longer is fine).
    :returns: ``{"sample_rate", "channels", "bits_per_sample", "total_samples",
        "duration_s", "min_block_size", "max_block_size", "md5"}``.
    :raises ValueError: if the bytes are not a FLAC stream whose first metadata
        block is a complete STREAMINFO.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise ValueError("expected bytes, got {0}".format(type(data).__name__))
    data = bytes(data)

    if len(data) < len(FLAC_MAGIC) or data[:4] != FLAC_MAGIC:
        raise ValueError("not a FLAC stream: missing 'fLaC' magic")
    if len(data) < _HEADER_SIZE:
        raise ValueError("truncated FLAC stream: no metadata block header")

    block_type = data[4] & 0x7F
    if block_type != STREAMINFO_TYPE:
        raise ValueError(
            "first metadata block is type {0}, expected STREAMINFO (0)".format(block_type)
        )

    block_len = int.from_bytes(data[5:8], "big")
    if block_len < STREAMINFO_SIZE:
        raise ValueError(
            "STREAMINFO block declares {0} bytes, minimum is {1}".format(block_len, STREAMINFO_SIZE)
        )

    body = data[_HEADER_SIZE:_HEADER_SIZE + STREAMINFO_SIZE]
    if len(body) < STREAMINFO_SIZE:
        raise ValueError(
            "truncated STREAMINFO: {0} of {1} bytes present".format(len(body), STREAMINFO_SIZE)
        )

    min_block, max_block = struct.unpack(">HH", body[0:4])
    packed = int.from_bytes(body[10:18], "big")
    sample_rate = (packed >> 44) & 0xFFFFF
    channels = ((packed >> 41) & 0x7) + 1
    bits_per_sample = ((packed >> 36) & 0x1F) + 1
    total_samples = packed & 0xFFFFFFFFF

    if sample_rate == 0:
        raise ValueError("STREAMINFO declares sample rate 0 (invalid FLAC)")

    return {
        "sample_rate": sample_rate,
        "channels": channels,
        "bits_per_sample": bits_per_sample,
        "total_samples": total_samples,
        "duration_s": total_samples / sample_rate,
        "min_block_size": min_block,
        "max_block_size": max_block,
        "md5": body[18:34],
    }


def build_streaminfo(sample_rate, channels, bits_per_sample, total_samples,
                     min_block_size=4096, max_block_size=4096, md5=b"\x00" * 16,
                     last_block=False):
    """Build minimal synthetic FLAC header bytes — the inverse of :func:`parse_streaminfo`.

    Used by the tests so the decoder is exercised round-trip without shipping
    binary fixtures into the repo.
    """
    if not 1 <= channels <= 8:
        raise ValueError("channels must be 1..8")
    if not 4 <= bits_per_sample <= 32:
        raise ValueError("bits_per_sample must be 4..32")

    packed = (
        (sample_rate & 0xFFFFF) << 44
        | ((channels - 1) & 0x7) << 41
        | ((bits_per_sample - 1) & 0x1F) << 36
        | (total_samples & 0xFFFFFFFFF)
    )
    body = (
        struct.pack(">HH", min_block_size, max_block_size)
        + (0).to_bytes(3, "big")          # min frame size (unknown)
        + (0).to_bytes(3, "big")          # max frame size (unknown)
        + packed.to_bytes(8, "big")
        + bytes(md5)
    )
    assert len(body) == STREAMINFO_SIZE, len(body)
    header = bytes([STREAMINFO_TYPE | (0x80 if last_block else 0)]) + \
        STREAMINFO_SIZE.to_bytes(3, "big")
    return FLAC_MAGIC + header + body
