"""High-level encrypt/decrypt of files, with validation and atomic writes.

The encrypted file is the raw cipher output (no header), as in Lab 1.
"""

import os
import tempfile
from pathlib import Path

from .cipher import decrypt_bytes, encrypt_bytes
from .constants import ENCRYPTED_EXTENSION, TYPE_JPEG, TYPE_PNG
from .errors import NotEncryptedFile, IoError
from .validation import detect_type, read_file, validate_image

_TYPE_EXTENSIONS = {TYPE_PNG: ".png", TYPE_JPEG: ".jpg"}


def suggest_encrypted_name(src):
    return str(Path(src).with_suffix(ENCRYPTED_EXTENSION))


def suggest_decrypted_name(src, image_type=None):
    """Output name for a decrypted file; image_type picks the extension."""
    ext = _TYPE_EXTENSIONS.get(image_type, ".png")
    return str(Path(src).with_suffix(ext))


def peek_image_type(src):
    """Image type of an encrypted file (from its first decrypted bytes), or None."""
    try:
        with open(src, "rb") as f:
            head = f.read(8)
    except OSError:
        return None
    return detect_type(decrypt_bytes(head))


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
    validate_image(src, data)
    _write_atomic(dst, encrypt_bytes(data, progress), overwrite)


def decrypt_file(src, dst, progress=None, overwrite=False):
    blob = read_file(src)
    data = decrypt_bytes(blob, progress)
    if detect_type(data) is None:
        raise NotEncryptedFile(
            "This is not a file encrypted by this tool: decrypting it does not "
            "give a PNG or JPEG image.")
    _write_atomic(dst, data, overwrite)
