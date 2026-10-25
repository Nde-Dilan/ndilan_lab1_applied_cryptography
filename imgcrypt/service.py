"""High-level encrypt/decrypt of files, with validation and atomic writes."""

import os
import tempfile
import zlib
from pathlib import Path

from . import container
from .cipher import decrypt_bytes, encrypt_bytes
from .constants import ENCRYPTED_EXTENSION, TYPE_JPEG, TYPE_PNG
from .errors import IntegrityError, IoError
from .validation import detect_type, read_file, validate_image

_TYPE_EXTENSIONS = {TYPE_PNG: ".png", TYPE_JPEG: ".jpg"}


def suggest_encrypted_name(src):
    return str(Path(src).with_suffix(ENCRYPTED_EXTENSION))


def suggest_decrypted_name(src, image_type=None):
    """Output name for a decrypted file; reads the header to pick the extension."""
    ext = _TYPE_EXTENSIONS.get(image_type, ".png")
    return str(Path(src).with_suffix(ext))


def peek_image_type(src):
    """Image type recorded in an encrypted file's header, or None if invalid."""
    try:
        with open(src, "rb") as f:
            return container.peek_type(f.read(container.HEADER_SIZE))
    except OSError:
        return None


def _write_atomic(dst, data, overwrite):
    dst = Path(dst)
    if dst.exists() and not overwrite:
        raise IoError(f"'{dst.name}' already exists.")
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dst.parent, prefix=".imgcrypt-", suffix=".tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_path, dst)
        tmp_path = None
    except OSError as e:
        raise IoError(f"Cannot write '{dst}': {e.strerror or e}") from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def encrypt_file(src, dst, progress=None, overwrite=False):
    data = read_file(src)
    image_type = validate_image(src, data)
    payload = encrypt_bytes(data, progress)
    blob = container.pack(image_type, zlib.crc32(data), payload)
    _write_atomic(dst, blob, overwrite)


def decrypt_file(src, dst, progress=None, overwrite=False):
    blob = read_file(src)
    image_type, crc, payload = container.unpack(blob)
    data = decrypt_bytes(payload, progress)
    if zlib.crc32(data) != crc or detect_type(data) != image_type:
        raise IntegrityError("Decryption failed: the encrypted file is corrupted.")
    _write_atomic(dst, data, overwrite)
