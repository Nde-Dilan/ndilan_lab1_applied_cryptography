"""Encrypt/decrypt byte strings: permute each byte, XOR with an LFSR byte."""

from .constants import KEY, LFSR_PERIOD
from .lfsr import Lfsr
from .permutation import INVERSE_TABLE, PERMUTE_TABLE

CHUNK_SIZE = 64 * 1024

# The byte keystream is the same for every file (LFSR restarts from KEY) and
# repeats after LFSR_PERIOD bytes (8 and 2^19-1 are coprime). Generate lazily.
_keystream = bytearray()
_lfsr = Lfsr(KEY)


def _extend_keystream(n):
    n = min(n, LFSR_PERIOD)
    while len(_keystream) < n:
        _keystream.append(_lfsr.next_byte())


def keystream_slice(start, length):
    """Keystream bytes [start, start+length) of the infinite repeating stream."""
    if length == 0:
        return b""
    start %= LFSR_PERIOD
    end = start + length
    _extend_keystream(min(end, LFSR_PERIOD))
    if end <= LFSR_PERIOD:
        return bytes(_keystream[start:end])
    parts = [bytes(_keystream[start:])]
    remaining = end - LFSR_PERIOD
    while remaining > 0:
        take = min(remaining, LFSR_PERIOD)
        _extend_keystream(take)
        parts.append(bytes(_keystream[:take]))
        remaining -= take
    return b"".join(parts)


def _xor(a, b):
    n = len(a)
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(n, "big")


def encrypt_bytes(data, progress=None, chunk_size=CHUNK_SIZE):
    """ciphertext = permute(byte) XOR keystream_byte. progress(0..1)."""
    total = len(data)
    out = bytearray()
    for pos in range(0, total, chunk_size):
        chunk = data[pos:pos + chunk_size].translate(PERMUTE_TABLE)
        out += _xor(chunk, keystream_slice(pos, len(chunk)))
        if progress:
            progress(min(1.0, (pos + len(chunk)) / total))
    if progress and total == 0:
        progress(1.0)
    return bytes(out)


def decrypt_bytes(data, progress=None, chunk_size=CHUNK_SIZE):
    """Inverse of encrypt_bytes."""
    total = len(data)
    out = bytearray()
    for pos in range(0, total, chunk_size):
        chunk = data[pos:pos + chunk_size]
        plain = _xor(chunk, keystream_slice(pos, len(chunk)))
        out += plain.translate(INVERSE_TABLE)
        if progress:
            progress(min(1.0, (pos + len(chunk)) / total))
    if progress and total == 0:
        progress(1.0)
    return bytes(out)
