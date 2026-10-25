"""Image type detection (spec section 4)."""

from pathlib import Path

from .constants import TYPE_JPEG, TYPE_PNG
from .errors import IoError, UnsupportedFileType

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"

_EXTENSION_TYPES = {".png": TYPE_PNG, ".jpg": TYPE_JPEG, ".jpeg": TYPE_JPEG}

SUPPORTED_MESSAGE = "Only PNG, JPG and JPEG images can be encrypted."


def detect_type(data):
    """Image type from the file's leading bytes, or None."""
    if data.startswith(PNG_SIGNATURE):
        return TYPE_PNG
    if data.startswith(JPEG_SIGNATURE):
        return TYPE_JPEG
    return None


def validate_image(path, data):
    """Return the image type code, or raise UnsupportedFileType.

    Both the extension and the content signature must indicate the same
    supported type.
    """
    ext_type = _EXTENSION_TYPES.get(Path(path).suffix.lower())
    if ext_type is None:
        raise UnsupportedFileType(f"'{Path(path).name}': {SUPPORTED_MESSAGE}")
    if not data:
        raise UnsupportedFileType(f"'{Path(path).name}' is empty.")
    content_type = detect_type(data)
    if content_type is None:
        raise UnsupportedFileType(
            f"'{Path(path).name}' is not a real image (its content is not "
            f"PNG or JPEG). {SUPPORTED_MESSAGE}"
        )
    if content_type != ext_type:
        raise UnsupportedFileType(
            f"'{Path(path).name}': the file extension does not match its content."
        )
    return content_type


def read_file(path):
    try:
        return Path(path).read_bytes()
    except OSError as e:
        raise IoError(f"Cannot read '{path}': {e.strerror or e}") from e
