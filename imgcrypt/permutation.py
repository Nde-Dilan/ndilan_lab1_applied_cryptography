"""Byte-level block permutation (spec section 3.2)."""

from .constants import PI

if sorted(PI) != list(range(1, 9)):
    raise ValueError("PI must be a permutation of 1..8")

# PI_INV[PI[i]] = i  (1-based values)
PI_INV = [0] * 8
for _i, _p in enumerate(PI, start=1):
    PI_INV[_p - 1] = _i
PI_INV = tuple(PI_INV)


def _apply(b, table):
    """Output bit i (index 1 = MSB) = input bit table[i]."""
    out = 0
    for i in range(8):
        out = (out << 1) | ((b >> (8 - table[i])) & 1)
    return out


def permute_byte(b):
    return _apply(b, PI)


def inverse_permute_byte(b):
    return _apply(b, PI_INV)


# 256-entry tables for use with bytes.translate().
PERMUTE_TABLE = bytes(permute_byte(b) for b in range(256))
INVERSE_TABLE = bytes(inverse_permute_byte(b) for b in range(256))
