"""Exceptions raised by imgcrypt. Messages are meant to be shown to the user."""


class ImageCryptError(Exception):
    """Base class for all expected failures."""


class UnsupportedFileType(ImageCryptError):
    """The input is not a PNG/JPG/JPEG image."""


class NotEncryptedFile(ImageCryptError):
    """The file does not decrypt to a PNG/JPEG, so it is not one of our files."""


class IoError(ImageCryptError):
    """A file could not be read or written."""
