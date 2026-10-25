"""Fixed parameters from Lab 1 (see spec.md sections 2-3)."""

# Initial 19-bit LFSR value (the key).
KEY = 0x67BD5

# LFSR p(x) = 1 + x^14 + x^17 + x^18 + x^19. Leftmost register bit is x^1 =
# bit 0, so term x^k is register bit k-1.
LFSR_WIDTH = 19
LFSR_TAPS = (13, 16, 17, 18)
LFSR_PERIOD = (1 << LFSR_WIDTH) - 1

# Block permutation, m = 8, 1-based, index 1 is the MSB of the byte.
PI = (2, 6, 3, 5, 1, 8, 4, 7)

# Container format (spec section 5).
MAGIC = b"IENC"
VERSION = 1
TYPE_PNG = 1
TYPE_JPEG = 2
ENCRYPTED_EXTENSION = ".ienc"
