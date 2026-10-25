The algorithm to be builtis one that takes in plaintext ob bits, break that down into groups of 8 bits, then for each groupd of 8 bits(byte) apply permutation using the Pi function from the class.


The key(0x67BD5) is 1100111101111010101 in binary, the LFSR shifts every cycle to generate new pseudo-random bits. 



One bit from the permutted plain text will be taken, compose with the MSB of the version of the key obtained after LFSR has been applied, The operation will continue until the data is full crypted