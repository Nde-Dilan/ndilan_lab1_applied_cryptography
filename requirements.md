# Requirements: Image Encryption Tool

This document says **what** the system must do. The **how** (algorithm, file format, architecture, build order) is in [spec.md](spec.md).

Keywords: **MUST** = mandatory, **SHOULD** = desirable, **MAY** = optional.
Each requirement has an ID so it can be traced to a spec section and a test.

## 1. Scope

A desktop application that (Lab 1 product cryptosystem) encrypts image files (PNG, JPG, JPEG) into an encrypted file, and decrypts those files back into the identical original image. Each byte is permuted, then XORed with a byte from an LFSR keystream (see spec).

Out of scope: key management, network features, encrypting non-image data, cryptographic strength beyond the class exercise.

## 2. Functional requirements

### 2.1 Action selection
- **FR-1** The UI MUST let the user choose between "Encrypt" and "Decrypt".
- **FR-2** The UI MUST have a Start button; no processing begins until it is pressed.
- **FR-3** The UI MUST let the user choose the input file and the output location/name.
- **FR-4** Start MUST be disabled until an action and a valid input file are selected.

### 2.2 Encryption
- **FR-5** Encrypt MUST accept only PNG, JPG and JPEG images.
- **FR-6** Encrypt MUST refuse any other file type, and MUST tell the user why.
- **FR-7** File type MUST be validated by file content (magic bytes), not just by extension.
- **FR-8** Every byte of the input MUST be permuted with the Pi function, then combined with the keystream (spec §3).
- **FR-9** The output MUST be an encrypted file that records enough information to restore the original image (spec §5).

### 2.3 Decryption
- **FR-10** Decrypt MUST accept only files produced by this tool, and MUST refuse anything else.
- **FR-11** Decrypt MUST output an image in its original format (PNG, JPG or JPEG).
- **FR-12** Decrypting an encrypted file MUST reproduce the original file byte-for-byte.

### 2.4 Feedback
- **FR-13** The UI MUST show a progress bar for both encryption and decryption.
- **FR-14** The UI MUST show a clear message when an error occurs (unsupported type, unreadable file, corrupt or foreign encrypted file, write failure).
- **FR-15** The UI MUST show a success message when an action finishes.
- **FR-16** The UI MUST stay responsive during processing (work runs off the UI thread).

## 3. Non-functional requirements
- **NFR-1** Correctness: for every supported image, `decrypt(encrypt(x)) == x`.
- **NFR-2** Determinism: the same input and key MUST always give the same output.
- **NFR-3** A failed or cancelled run MUST NOT leave a partial output file behind, and MUST NOT overwrite an existing file without confirmation.
- **NFR-4** Files up to 50 MB SHOULD process in reasonable time (target under 30 s on a typical laptop).
- **NFR-5** The crypto core MUST be independent of the UI so it can be tested without one.
- **NFR-6** The project MUST have automated tests for the permutation, LFSR and round trip.
- **NFR-7** Implementation language: Python 3 (the project lives in a Python projects folder). Dependencies SHOULD be limited to the standard library (Tkinter for the UI).

## 4. Constraints
- **C-1** Key: `0x67BD5` (19 bits, `1100111101111010101`), fixed in the program.
- **C-2** The algorithm follows the Lab 1 definition: Pi permutation on each byte, then XOR with a byte from the LFSR (polynomial `1 + x^14 + x^17 + x^18 + x^19`).
- **C-3** The UI MUST be Python with Tkinter, with encrypt/decrypt selection, input file, output file and a Start button (Lab 1 §1).
- **C-4** Interoperability: the bit-ordering rules in spec §2 MUST be followed exactly.

## 5. Resolved details and remaining question
The Lab 1 handout and slide 19 supply the algorithm details: Pi table, LFSR polynomial `1 + x^14 + x^17 + x^18 + x^19`, bit-ordering rules, XOR combination, and byte-wise operation. They are recorded in spec §2-3.

| # | Item | Status |
|---|------|--------|
| Q1 | Pi table | Resolved: `2 6 3 5 1 8 4 7` |
| Q2 | LFSR taps/direction | Resolved: taps at register bits 13, 16, 17, 18; feedback enters on the left |
| Q3 | Combination operation | Resolved: XOR |
| Q4 | Output bit | Resolved: MSB shifted out; first output = MSB of seed |
| Q5 | LFSR restart per file | Assumed yes (needed for decrypt) |
| Q6 | Key | Fixed `0x67BD5` per the slide |
| Q7 | Pi direction: output bit i = input bit pi(i), or input bit i goes to pi(i)? | **Open**: spec assumes the former; confirm before build step 4 |

## 6. Acceptance criteria
1. Encrypting a PNG, a JPG and a JPEG each produces an encrypted file; decrypting each gives back a file with the identical hash.
2. Selecting a `.txt`, `.pdf`, or a `.png` that is really a text file is rejected with a message (FR-6, FR-7).
3. Decrypting a plain image, a random file, or a truncated or modified encrypted file is rejected with a message (FR-10, FR-14).
4. The progress bar goes from 0 to 100% during a run on a multi-MB image.
5. All automated tests pass.
