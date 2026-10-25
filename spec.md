# Specification: Image Encryption Tool

This document says **how** the system works. The **what** is in [requirements.md](requirements.md); requirement IDs are cited as (FR-n / NFR-n).


## 1. Overview

```
 input image -> validate -> read bytes -> per byte: Pi permute -> XOR with LFSR byte -> write raw ciphertext
                                                                  (LFSR seed 0x67BD5)
```

Decryption is the reverse: read the file, XOR with the same LFSR byte stream, apply inverse Pi, check the result is a PNG/JPEG, write original bytes. The system is the "simple product cryptosystem" from the slide: a block permutation cipher (m = 8) followed by an XOR with an LFSR keystream.

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
- For Decrypt, the decrypted result must pass the signature check (§5).

## 5. Encrypted file format (FR-9, FR-10, FR-11)

The encrypted file is the **raw cipher output**: exactly one ciphertext byte per input byte, no header, no padding. This is the Lab 1 format, so our output is byte-identical to any other correct implementation and we can decrypt a reference `.enc` file.

Consequences:
- Output size equals input size.
- The original image type is not stored. Decrypt recovers it from the decrypted bytes (PNG or JPEG signature, §4) and suggests `.png` or `.jpg` accordingly.
- Decrypt cannot tell a foreign file from one of ours before decrypting. It decrypts in memory, then accepts the result only if it begins with a PNG or JPEG signature (the same check as §4). Anything else raises `NotEncryptedFile`, and no output file is written (NFR-3). A plain image, a text file, or random bytes fed to Decrypt all fail this check (a random file passes with probability about 2^-24 or less).
- Corruption after the first few bytes is not detected (there is no checksum); only damage to the first 3-8 bytes shows up as a rejection.

Default names: Encrypt -> `<name>.enc`; Decrypt -> `<name>.png` or `<name>.jpg` by detected type.

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
    service.py       # encrypt_file / decrypt_file: ties it all together, atomic writes
    errors.py        # ImageCryptError and subclasses
  ui/
    app.py           # Tkinter window
  tests/
    test_permutation.py
    test_lfsr.py
    test_cipher.py
    test_validation.py
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
- Errors are raised as `ImageCryptError` subclasses: `UnsupportedFileType`, `NotEncryptedFile`, `IoError`. Messages are user-readable.

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
| Service | image round trip gives identical SHA-256; encrypted file equals the raw cipher output with the same length as the input; a plain image, text or random file given to Decrypt → `NotEncryptedFile`; failure leaves no output file; progress reaches 1.0 |

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
| 6 | `service.py` with atomic writes, progress callback | 4–5 | image round trips are byte-identical |
| 7 | Performance pass (lookup tables, chunked keystream) | 6 | 50 MB under target, same vectors still pass |
| 8 | Tkinter UI wired to the service | 6 | manual run covers acceptance criteria 1–4 |
| 9 | End-to-end check against all acceptance criteria; README with run instructions | all | requirements §6 all pass |

## 9. Known limitations
- Same key and same keystream for every file: two files encrypted with this tool leak the XOR of their (permuted) contents. Acceptable for the class exercise; a real system would use a per-file random IV/nonce.
- The 19-bit LFSR period is 524,287 bits; since 8 and 524,287 are coprime, the byte keystream repeats only after 524,287 bytes (~512 KB). Larger images reuse the pad.
- A linear LFSR keystream is breakable from a small amount of known plaintext (image headers are predictable).
- The raw format has no integrity check: corruption or tampering of the encrypted file is not detected, except damage near the start that breaks the image signature.
