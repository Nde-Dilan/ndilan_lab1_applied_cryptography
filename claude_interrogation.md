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