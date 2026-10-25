import os
import random
import unittest

from imgcrypt import cipher
from imgcrypt.constants import KEY, LFSR_PERIOD, PI
from imgcrypt.lfsr import Lfsr
from imgcrypt.permutation import (
    INVERSE_TABLE, PERMUTE_TABLE, inverse_permute_byte, permute_byte,
)

PLAIN = bytes.fromhex("00 01 80 FF A5 12 89 50")
CIPHER = bytes.fromhex("F3 5A 05 99 AA FE CB 9F")


class PermutationTests(unittest.TestCase):
    def test_pi_is_permutation(self):
        self.assertEqual(sorted(PI), list(range(1, 9)))

    def test_vectors(self):
        for b, want in [(0x00, 0x00), (0x01, 0x04), (0x80, 0x08),
                        (0xFF, 0xFF), (0x12, 0x03), (0xA5, 0x6C)]:
            self.assertEqual(permute_byte(b), want, hex(b))

    def test_inverse_all_bytes(self):
        for b in range(256):
            self.assertEqual(inverse_permute_byte(permute_byte(b)), b)

    def test_tables_match_functions(self):
        self.assertEqual(PERMUTE_TABLE, bytes(permute_byte(b) for b in range(256)))
        self.assertEqual(INVERSE_TABLE, bytes(inverse_permute_byte(b) for b in range(256)))

    def test_is_bijection(self):
        self.assertEqual(len(set(PERMUTE_TABLE)), 256)


class LfsrTests(unittest.TestCase):
    def test_first_bytes(self):
        l = Lfsr(KEY)
        got = bytes(l.next_byte() for _ in range(8))
        self.assertEqual(got, bytes.fromhex("F3 5E 0D 66 C6 FD D7 1D"))
        self.assertEqual(l.state, 0x2E522)

    def test_first_output_bit_is_seed_msb(self):
        self.assertEqual(Lfsr(KEY).next_bit(), (KEY >> 18) & 1)

    def test_period(self):
        l = Lfsr(KEY)
        for n in range(1, LFSR_PERIOD + 1):
            l.next_bit()
            if l.state == KEY:
                break
        self.assertEqual(n, LFSR_PERIOD)


class CipherTests(unittest.TestCase):
    def test_vector(self):
        self.assertEqual(cipher.encrypt_bytes(PLAIN), CIPHER)
        self.assertEqual(cipher.decrypt_bytes(CIPHER), PLAIN)

    def test_matches_bitwise_reference(self):
        data = os.urandom(5000)
        l = Lfsr(KEY)
        ref = bytes(permute_byte(b) ^ l.next_byte() for b in data)
        self.assertEqual(cipher.encrypt_bytes(data, chunk_size=777), ref)

    def test_round_trip_sizes(self):
        for n in (0, 1, 7, 65535, 65536, 65537, 200_000):
            data = os.urandom(n)
            self.assertEqual(cipher.decrypt_bytes(cipher.encrypt_bytes(data)), data, n)

    def test_keystream_wraps_at_period(self):
        a = cipher.keystream_slice(0, 100)
        b = cipher.keystream_slice(LFSR_PERIOD, 100)
        self.assertEqual(a, b)
        span = cipher.keystream_slice(LFSR_PERIOD - 50, 100)
        self.assertEqual(span, cipher.keystream_slice(LFSR_PERIOD - 50, 50) + a[:50])

    def test_chunking_independent(self):
        data = random.randbytes(300_000)
        self.assertEqual(cipher.encrypt_bytes(data, chunk_size=1000),
                         cipher.encrypt_bytes(data, chunk_size=65536))

    def test_progress(self):
        seen = []
        cipher.encrypt_bytes(os.urandom(200_000), seen.append)
        self.assertEqual(seen[-1], 1.0)
        self.assertEqual(seen, sorted(seen))
        empty = []
        cipher.encrypt_bytes(b"", empty.append)
        self.assertEqual(empty, [1.0])


if __name__ == "__main__":
    unittest.main()
