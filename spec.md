# Specification: Image Encryption Tool

This document says **how** the system works. The **what** is in [requirements.md](requirements.md); requirement IDs are cited as (FR-n / NFR-n).


## 1. Overview

```
 input image -> validate -> read bytes -> per byte: Pi permute -> XOR with LFSR byte -> write container
                                                                  (LFSR seed 0x67BD5)
```

Decryption is the reverse: read container, XOR with the same LFSR byte stream, apply inverse Pi, write original bytes. The system is the "simple product cryptosystem" from the slide: a block permutation cipher (m = 8) followed by an XOR with an LFSR keystream.

## 2. Bit-numbering conventions (Lab 1 §1.b)

| Item | Convention |
|------|-----------|
| LFSR register | 19 bits. The **leftmost** bit is "x" in the polynomial and is the **LSB** (bit 0). The rightmost is the **MSB** (bit 18) |
| Seed | Loaded as an integer: the LSB of the seed goes into the LSB (bit 0) of the register |
| Shift direction | Register shifts toward the MSB; the feedback bit enters on the left (bit 0); the MSB is shifted out |
| LFSR output bit | The bit shifted out, i.e. the **MSB** of the register. The first output bit is the MSB of the seed |
| LFSR output byte | The first output bit becomes the **LSB** of the byte, the eighth becomes the MSB |
| Pi indexing | Index 1 is the **MSB** of the byte, index 8 the LSB |
| Data order | Bytes in file order |

## 3. Cryptographic algorithm

### 3.1 Key
`KEY = 0x67BD5 = 0b1100111101111010101` (19 bits), the initial LFSR state (slide: "for lab 1, use as initial 19 bit key").

### 3.2 Pi permutation (byte level)
From the slide, m = 8:

| i | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| pi(i) | 2 | 6 | 3 | 5 | 1 | 8 | 4 | 7 |

Index 1 is the MSB. Direction (decided, not stated on the slide): output bit `i` = input bit `pi(i)` (the textbook block-permutation cipher, `y_i = x_pi(i)`). The reverse reading (input bit `i` moves to position `pi(i)`) would give a different ciphertext; if a reference output ever disagrees, flip the direction in `permutation.py` and update the vectors in §3.3.1.

Decrypt uses the inverse: `PI_INV[pi(i)] = i`, computed at load time. The program verifies at import that `PI` is a permutation of 1..8.

```python
PI = (2, 6, 3, 5, 1, 8, 4, 7)          # 1-based, index 1 = MSB
def permute_byte(b):
    bits = [(b >> (8 - i)) & 1 for i in range(1, 9)]
    out = 0
    for i in range(8):
        out = (out << 1) | bits[PI[i] - 1]
    return out
```

### 3.3 LFSR keystream
Polynomial: `p(x) = 1 + x^14 + x^17 + x^18 + x^19`.

With the leftmost bit = x^1 = bit 0, term `x^k` is register bit `k-1`. The tap bits are therefore **13, 16, 17, 18** (0-based). The "1" term is the feedback bit itself.

Each clock:
1. `out = (state >> 18) & 1` (the MSB, shifted out)
2. `fb = bit13 ^ bit16 ^ bit17 ^ bit18` of the current state
3. `state = ((state << 1) | fb) & 0x7FFFF`

Output byte: collect 8 clocks, first output bit -> bit 0 of the byte, ..., eighth -> bit 7.

The LFSR is re-initialised to `KEY` at the start of every file (so decrypt reproduces the same stream). The polynomial is primitive: the register period is 2^19 - 1 = 524,287 clocks (verified).

```python
class Lfsr:
    WIDTH, MASK, TAPS = 19, (1 << 19) - 1, (13, 16, 17, 18)
    def __init__(self, seed): self.state = seed
    def next_bit(self):
        out = (self.state >> 18) & 1
        fb = 0
        for t in self.TAPS:
            fb ^= (self.state >> t) & 1
        self.state = ((self.state << 1) | fb) & self.MASK
        return out
    def next_byte(self):
        b = 0
        for i in range(8):
            b |= self.next_bit() << i
        return b
```

### 3.3.1 Test vectors (computed from the rules above)
- First 8 LFSR output bytes from the seed: `F3 5E 0D 66 C6 FD D7 1D`; register state after those 64 clocks: `0x2E522`.
- First output byte is `F3`: seed bits MSB-first are `1,1,0,0,1,1,1,1,...`, and the first bit lands in the LSB.
- `permute_byte`: `00->00`, `01->04`, `80->08`, `FF->FF`, `12->03`, `A5->6C`.
- Cipher: plaintext `00 01 80 FF A5 12 89 50` -> ciphertext `F3 5A 05 99 AA FE CB 9F`.

### 3.4 Encrypt / decrypt a byte
```
encrypt_byte(b):  return permute(b, PI) XOR lfsr.next_byte()
decrypt_byte(c):  return permute(c XOR lfsr.next_byte(), PI_INV)
```
XOR is self-inverse, so the same keystream both encrypts and decrypts.

### 3.5 Performance note
A bit-by-bit Python loop is slow for large images. Acceptable for a first version; to meet NFR-4, optimise later by:
1. Precomputing a 256-entry table for `permute` / `inverse permute`.
2. Precomputing the keystream (524,287 bytes) and cycling through it.
Any optimisation MUST pass the same test vectors as the plain version.

## 4. File validation (FR-5, FR-6, FR-7, FR-10)

Supported inputs for Encrypt, by magic bytes:
| Type | Signature (start of file) |
|------|---------------------------|
| PNG | `89 50 4E 47 0D 0A 1A 0A` |
| JPEG (.jpg/.jpeg) | `FF D8 FF` |

Rules:
- Extension must be `.png`, `.jpg` or `.jpeg` (case-insensitive) **and** the magic bytes must match. Either failing means refuse.
- Empty files are refused.
- For Decrypt, the container magic and header checks in §5 must pass.

## 5. Encrypted container format (FR-9, FR-10, FR-11)

Needed so Decrypt can tell our files from others and restore the original format. Little-endian integers.

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0 | 4 | magic | ASCII `IENC` |
| 4 | 1 | version | `1` |
| 5 | 1 | original type | `1` = PNG, `2` = JPEG |
| 6 | 8 | payload length | number of encrypted bytes |
| 14 | 4 | CRC32 of the **original** plaintext | detects corruption / wrong key after decrypt |
| 18 | N | payload | encrypted bytes |

Decrypt checks: magic matches, version known, type known, file size = 18 + payload length, and after decryption the CRC32 matches and the magic bytes of the result match the recorded type. Any failure raises an error and no output file is kept (NFR-3).

The header is stored unencrypted; it reveals only the image type and size.

The default output name: Encrypt → `<name>.ienc`; Decrypt → `<name>.png` or `<name>.jpg` based on the recorded type.

## 6. Architecture

```
ndilan_hw1/
  imgcrypt/
    __init__.py
    constants.py     # KEY, PI, MAGIC values
    permutation.py   # permute_byte, inverse
    lfsr.py          # Lfsr class
    cipher.py        # encrypt_bytes / decrypt_bytes (with progress callback)
    validation.py    # type detection, file checks
    container.py     # pack / unpack header
    service.py       # encrypt_file / decrypt_file: ties it all together, atomic writes
    errors.py        # ImageCryptError and subclasses
  ui/
    app.py           # Tkinter window
  tests/
    test_permutation.py
    test_lfsr.py
    test_cipher.py
    test_validation.py
    test_container.py
    test_service.py
  main.py            # starts the UI
```

Rules: `imgcrypt` imports nothing from `ui` (NFR-5). The UI talks only to `service`.

### 6.1 Service API
```python
def encrypt_file(src: Path, dst: Path, progress: Callable[[float], None] | None = None) -> None
def decrypt_file(src: Path, dst: Path, progress: Callable[[float], None] | None = None) -> None
```
- `progress` receives a value 0.0–1.0, called at least every 1% of data (or every 64 KB, whichever is larger).
- Both write to a temp file in the destination folder, then rename on success; delete the temp file on any failure (NFR-3).
- Errors are raised as `ImageCryptError` subclasses: `UnsupportedFileType`, `InvalidContainer`, `IntegrityError`, `IoError`. Messages are user-readable.

### 6.2 UI behaviour (FR-1 to FR-4, FR-13 to FR-16)
- Radio buttons: Encrypt / Decrypt.
- "Browse" buttons for input and output; output name auto-suggested (§5).
- Start button, disabled until the action and input are valid.
- Determinate progress bar and percentage label.
- Status line for success; `messagebox` for errors.
- Work runs in a worker thread; progress goes back to the UI thread via `queue` + `after()`. Controls are disabled while running.

## 7. Test plan

| Area | Tests |
|------|-------|
| Permutation | `PI` is a valid permutation; `inverse(permute(b)) == b` for all 256 values; vectors from §3.3.1 |
| LFSR | first 8 bytes match §3.3.1; state after 64 clocks is `0x2E522`; state returns to the seed after 524,287 clocks |
| Cipher | round trip on empty, 1 byte, random 1 MB; ciphertext vector from §3.3.1 |
| Validation | accepts real PNG/JPG; rejects `.txt`, `.pdf`, a text file renamed `.png`, empty file |
| Container | pack/unpack round trip; rejects bad magic, bad version, truncated, wrong length |
| Service | image round trip gives identical SHA-256; tampered file → `IntegrityError`; failure leaves no output file; progress reaches 1.0 |

## 8. Build plan (step by step)

Each step ends with passing tests and a commit.

| Step | Deliverable | Needs | Done when |
|------|-------------|-------|-----------|
| 0 | Done: details taken from the Lab 1 handout and slide 19; Pi direction decided (output bit i = input bit pi(i)) | – | – |
| 1 | Project skeleton, `constants.py`, `errors.py`, test runner (`pytest` or `unittest`) | – | empty tests run |
| 2 | `permutation.py` + tests | – | permutation tests pass |
| 3 | `lfsr.py` + tests | – | LFSR matches §3.3.1 |
| 4 | `cipher.py` + round-trip tests | – | `decrypt(encrypt(x)) == x` |
| 5 | `validation.py` + tests | – | FR-5/6/7 tests pass |
| 6 | `container.py` + tests | – | FR-9/10 tests pass |
| 7 | `service.py` with atomic writes, progress callback | 4–6 | image round trips are byte-identical |
| 8 | Performance pass (lookup tables, chunked keystream) | 7 | 50 MB under target, same vectors still pass |
| 9 | Tkinter UI wired to the service | 7 | manual run covers acceptance criteria 1–4 |
| 10 | End-to-end check against all acceptance criteria; README with run instructions | all | requirements §6 all pass |

## 9. Known limitations
- Same key and same keystream for every file: two files encrypted with this tool leak the XOR of their (permuted) contents. Acceptable for the class exercise; a real system would use a per-file random IV/nonce.
- The 19-bit LFSR period is 524,287 bits; since 8 and 524,287 are coprime, the byte keystream repeats only after 524,287 bytes (~512 KB). Larger images reuse the pad.
- A linear LFSR keystream is breakable from a small amount of known plaintext (image headers are predictable).
- The CRC32 detects accidental corruption only, not deliberate tampering.
