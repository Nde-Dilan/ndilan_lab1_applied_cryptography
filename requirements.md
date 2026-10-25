The algorithm to be builtis one that takes in plaintext ob bits, break that down into groups of 8 bits, then for each groupd of 8 bits(byte) apply permutation using the Pi function from the class.


The key(0x67BD5) is 1100111101111010101 in binary, the LFSR shifts every cycle to generate new pseudo-random bits. 



One bit from the permutted plain text will be taken, compose with the MSB of the version of the key obtained after LFSR has been applied, The operation will continue until the data is full crypted.


---
The system should allow users to select the action they want to perform

The UI should allow the user to select “encrypt” or “decrypt”.

The UI should have a start button to let the user choose when to start the chosen action.


The system should take in ONLY images(PNG,JPG,JPEG) and output an encrypted version for the ENCRYPION action.

The system should notify the user with a progress bar of the progression of the action[ENCRYPTION|DECRYPTION]

The system should let users know when an ERROR has occured

The system shoul take in ONLY encrypted files and output ONLY images(PNG,JPG,JPEG) for the DECRYPTION action.

The program should permute every byte(group of 8bits) of the plaintext input.


The system should refuse any other type of documents for encryption.