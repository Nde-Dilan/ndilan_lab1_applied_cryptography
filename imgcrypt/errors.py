"""Exceptions raised by imgcrypt. Messages are meant to be shown to the user."""


class ImageCryptError(Exception):
    """Base class for all expected failures."""


class UnsupportedFileType(ImageCryptError):
    """The input is not a PNG/JPG/JPEG image."""


class InvalidContainer(ImageCryptError):
    """The file is not a valid encrypted file produced by this tool."""


class IntegrityError(ImageCryptError):
    """Decrypted data failed the integrity check."""


class IoError(ImageCryptError):
    """A file could not be read or written."""
