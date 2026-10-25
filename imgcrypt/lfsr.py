"""19-bit LFSR keystream generator (spec section 3.3)."""

from .constants import KEY, LFSR_TAPS, LFSR_WIDTH


class Lfsr:
    MASK = (1 << LFSR_WIDTH) - 1

    def __init__(self, seed=KEY):
        self.state = seed & self.MASK

    def next_bit(self):
        """Shift once; return the bit shifted out (the MSB)."""
        out = (self.state >> (LFSR_WIDTH - 1)) & 1
        fb = 0
        for t in LFSR_TAPS:
            fb ^= (self.state >> t) & 1
        self.state = ((self.state << 1) | fb) & self.MASK
        return out

    def next_byte(self):
        """First output bit becomes the LSB of the byte."""
        b = 0
        for i in range(8):
            b |= self.next_bit() << i
        return b
