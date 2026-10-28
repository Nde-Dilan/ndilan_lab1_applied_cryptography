Index 1 is the MSB. [CONFIRM] Direction: output bit i = input bit pi(i) (the textbook block-permutation cipher, y_i =
  x_pi(i)). The slide does not state it explicitly; the reverse reading (input bit i moves to position pi(i)) would
  give a different ciphertext. Check against the instructor or a classmate's output before step 4.   I don't understand
  this description, what is the problem and what are the consequences?


  Answer: 

    The slide gives π(1)=2, π(2)=6, π(3)=3, π(4)=5, π(5)=1, π(6)=8, π(7)=4, π(8)=7. "Permute the bits of a byte using π"
  can mean two things:

  - Reading A (what I assumed): output position i takes its value from input bit π(i). For example, output bit 1 (the
    MSB) is a copy of input bit 2.
  - Reading B: input bit i moves to output position π(i). For example, input bit 1 (the MSB) goes to position 2.

Conclusion: We will kepp Reading A since it follows what is said in the notes.



Now, the encrypted file we need to test against has an extension of enc, ours is ienc, why is that?

.ienc was my own choice, not something from the lab. I picked it in the spec as a name tied to my IENC header marker,
  and nothing in the handout or slides asks for it. I should have used the plain .enc the lab implies.

  The extension is the smaller problem. My format wraps the ciphertext in an 18-byte header (marker, image type, length,
  checksum). A reference .enc file is probably the raw permute-then-XOR output with no header.

  - Our Decrypt would reject the reference file. It would say "Not an encrypted file made by this tool".
  - Our Encrypt output wouldn't match the reference byte for byte. It would differ by the header, and the checksum field
    depends on the plaintext.

  I flagged the header risk when I finished the build, but I should have raised it earlier.

  There are two ways to fix it:
  1. Raw format, matching the lab (my recommendation). The file is just the ciphertext, saved as .enc. It would match
     the reference exactly and decrypt the reference file. The cost is that Decrypt can no longer tell "not our file"
     from "our file". A wrong or corrupt file would decrypt to garbage. We'd refuse it only if the result isn't a valid
     PNG or JPEG, and the output extension (.png or .jpg) would come from the decrypted content instead of a header.
  2. Keep the header and add a raw mode. More code and more UI, and I think the lab doesn't need it.

  Which do you want? I'd go with option 1, rename the extension to .enc, and update the spec, tests and UI.

  Conclusion: The encrypted extension is compliant to what the lab is asking for

 UI redesign (`ui/app.py`)
Request: make the next action obvious and tell the user what is happening at every stage. I rewrote the front end as a four-step flow:
- **Layout:** Step 1 Choose action, Step 2 Select file, Step 3 Choose output location, Step 4 Encrypt/Decrypt, each with a bold label and consistent spacing.
- **File selection:** one large clickable area plus a "Browse files…" button, showing the selected filename.
- **Output name:** suggested automatically (e.g. `a.png` -> `a.enc`) and editable. I kept the Lab 1 `.enc` extension instead of the `.encrypted` example in the request.
- **Status line:** colored, with explicit states: "Ready to encrypt", "Encrypting… 45%", "Encryption complete. Saved to …", and actionable errors. While inputs are incomplete it says what to do next.
- **Primary button:** large, labelled "Encrypt file" / "Decrypt file", and disabled until the input file exists, the output folder exists, and input and output differ.
- Changing the action, input or output clears the previous result and resets the progress bar. The overwrite confirmation dialog stays.
- A headless smoke test of the encrypt flow and the action switch passed. The existing tests were not run (pytest is not installed).

How the cipher works (checked against `imgcrypt/lfsr.py`, `cipher.py`, `permutation.py`)
My understanding was mostly right, with two corrections:
- The LFSR is **19 bits**, not 20. Key `0x67BD5`, p(x) = 1 + x^14 + x^17 + x^18 + x^19, feedback = XOR of register bits 13, 16, 17, 18 (0-based). Period is 2^19 - 1.
- The permutation works **per byte** (m = 8) and nothing moves between bytes. Output bit i = input bit pi(i), counting from the MSB, with pi = (2, 6, 3, 5, 1, 8, 4, 7).

Per byte: permute the bits, take 8 LFSR output bits as a keystream byte (first bit out is the LSB), XOR the two. The bit shifted out of the register is the keystream bit, the register shifts along, and a new feedback bit enters at the start. Decryption XORs with the same keystream, then applies the inverse permutation.
Side effect: the LFSR restarts from the same key for every file, so every file uses the same keystream. That is acceptable for the lab but not secure in practice.

Recovered first draft
I retrieved my original requirements draft from git (commit `6acd5c6`, the last version before the rewrite in `bcdad27`) and saved it as `requirements_v1.md`.
