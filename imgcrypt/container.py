"""Encrypted file container (spec section 5)."""

import struct

from .constants import MAGIC, TYPE_JPEG, TYPE_PNG, VERSION
from .errors import InvalidContainer

_HEADER = struct.Struct("<4sBBQI")
HEADER_SIZE = _HEADER.size  # 18


def pack(image_type, plaintext_crc, payload):
    return _HEADER.pack(MAGIC, VERSION, image_type, len(payload), plaintext_crc) + payload


def unpack(blob):
    """Return (image_type, plaintext_crc, payload) or raise InvalidContainer."""
    if len(blob) < HEADER_SIZE:
        raise InvalidContainer("Not an encrypted file made by this tool (too short).")
    magic, version, image_type, length, crc = _HEADER.unpack_from(blob)
    if magic != MAGIC:
        raise InvalidContainer("Not an encrypted file made by this tool.")
    if version != VERSION:
        raise InvalidContainer(f"Unsupported encrypted file version {version}.")
    if image_type not in (TYPE_PNG, TYPE_JPEG):
        raise InvalidContainer("Encrypted file has an unknown image type.")
    if len(blob) != HEADER_SIZE + length:
        raise InvalidContainer("Encrypted file is truncated or has extra data.")
    return image_type, crc, blob[HEADER_SIZE:]


def peek_type(head):
    """Image type from the first HEADER_SIZE bytes, or None if not our header."""
    if len(head) < HEADER_SIZE:
        return None
    magic, version, image_type, _, _ = _HEADER.unpack_from(head)
    if magic != MAGIC or version != VERSION or image_type not in (TYPE_PNG, TYPE_JPEG):
        return None
    return image_type
