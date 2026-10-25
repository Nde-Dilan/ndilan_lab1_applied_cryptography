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
