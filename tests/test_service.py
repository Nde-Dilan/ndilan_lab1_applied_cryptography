import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from imgcrypt import cipher, service
from imgcrypt.constants import TYPE_JPEG, TYPE_PNG
from imgcrypt.errors import IoError, NotEncryptedFile, UnsupportedFileType
from imgcrypt.validation import PNG_SIGNATURE, detect_type, validate_image


def fake_png(n=300_000):
    return PNG_SIGNATURE + os.urandom(n)


def fake_jpeg(n=100_000):
    return b"\xff\xd8\xff\xe0" + os.urandom(n)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ValidationTests(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(detect_type(fake_png()), TYPE_PNG)
        self.assertEqual(detect_type(fake_jpeg()), TYPE_JPEG)
        self.assertIsNone(detect_type(b"hello"))

    def test_accepts(self):
        self.assertEqual(validate_image("a.PNG", fake_png()), TYPE_PNG)
        self.assertEqual(validate_image("a.jpg", fake_jpeg()), TYPE_JPEG)
        self.assertEqual(validate_image("a.jpeg", fake_jpeg()), TYPE_JPEG)

    def test_rejects(self):
        for name, data in [("a.txt", b"hello"), ("a.pdf", b"%PDF-1.4"),
                           ("a.png", b"just text"), ("a.png", b""),
                           ("a.png", fake_jpeg()), ("a.jpg", fake_png()),
                           ("noext", fake_png())]:
            with self.assertRaises(UnsupportedFileType, msg=name):
                validate_image(name, data)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def roundtrip(self, name, data):
        src = self.d / name
        src.write_bytes(data)
        enc = self.d / (name + ".enc")
        out = self.d / ("out_" + name)
        service.encrypt_file(src, enc)
        self.assertEqual(enc.read_bytes(), cipher.encrypt_bytes(data))  # raw, no header
        self.assertEqual(len(enc.read_bytes()), len(data))
        self.assertNotEqual(enc.read_bytes(), data)
        service.decrypt_file(enc, out)
        self.assertEqual(sha(out), sha(src))

    def test_round_trips(self):
        self.roundtrip("a.png", fake_png())
        self.roundtrip("b.jpg", fake_jpeg())
        self.roundtrip("c.jpeg", fake_jpeg(1000))
        self.roundtrip("big.png", fake_png(700_000))  # longer than part of the keystream cycle

    def test_encrypt_rejects_non_images(self):
        for name, data in [("a.txt", b"hello"), ("fake.png", b"text in disguise")]:
            src = self.d / name
            src.write_bytes(data)
            dst = self.d / "o.enc"
            with self.assertRaises(UnsupportedFileType):
                service.encrypt_file(src, dst)
            self.assertFalse(dst.exists())

    def test_decrypt_rejects_foreign_files(self):
        for data in (fake_png(), fake_jpeg(), os.urandom(500), b"", b"plain text file"):
            src = self.d / "x.enc"
            src.write_bytes(data)
            with self.assertRaises(NotEncryptedFile):
                service.decrypt_file(src, self.d / "o.png")
            self.assertFalse((self.d / "o.png").exists())

    def test_corrupted_first_bytes_rejected(self):
        src = self.d / "a.png"
        src.write_bytes(fake_png(1000))
        enc = self.d / "a.enc"
        service.encrypt_file(src, enc)
        blob = bytearray(enc.read_bytes())
        blob[0] ^= 0xFF
        enc.write_bytes(bytes(blob))
        out = self.d / "o.png"
        with self.assertRaises(NotEncryptedFile):
            service.decrypt_file(enc, out)
        self.assertFalse(out.exists())
        self.assertEqual([p.name for p in self.d.iterdir() if p.suffix == ".tmp"], [])

    def test_no_overwrite_by_default(self):
        src = self.d / "a.png"
        src.write_bytes(fake_png(100))
        dst = self.d / "a.enc"
        dst.write_bytes(b"precious")
        with self.assertRaises(IoError):
            service.encrypt_file(src, dst)
        self.assertEqual(dst.read_bytes(), b"precious")
        service.encrypt_file(src, dst, overwrite=True)
        self.assertNotEqual(dst.read_bytes(), b"precious")

    def test_missing_input_and_bad_destination(self):
        with self.assertRaises(IoError):
            service.encrypt_file(self.d / "missing.png", self.d / "o.enc")
        src = self.d / "a.png"
        src.write_bytes(fake_png(100))
        with self.assertRaises(IoError):
            service.encrypt_file(src, self.d / "no_such_dir" / "o.enc")

    def test_progress_reaches_one(self):
        src = self.d / "a.png"
        src.write_bytes(fake_png(300_000))
        seen = []
        service.encrypt_file(src, self.d / "a.enc", seen.append)
        self.assertEqual(seen[-1], 1.0)
        self.assertGreater(len(seen), 2)

    def test_names_and_peek(self):
        src = self.d / "a.png"
        src.write_bytes(fake_png(100))
        enc = self.d / "a.enc"
        service.encrypt_file(src, enc)
        self.assertEqual(service.peek_image_type(enc), TYPE_PNG)
        self.assertIsNone(service.peek_image_type(src))
        self.assertIsNone(service.peek_image_type(self.d / "missing"))
        self.assertTrue(service.suggest_encrypted_name(src).endswith("a.enc"))
        self.assertTrue(service.suggest_decrypted_name(enc, TYPE_JPEG).endswith("a.jpg"))


if __name__ == "__main__":
    unittest.main()
