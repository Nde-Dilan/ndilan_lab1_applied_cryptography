# Image Encryption Tool (Lab 1)

Product cryptosystem: each byte is permuted with the Lab 1 Pi table, then XORed with a byte from a 19-bit LFSR (key `0x67BD5`, polynomial `1 + x^14 + x^17 + x^18 + x^19`). See [requirements.md](requirements.md) and [spec.md](spec.md).

## Run
```
python main.py
```
Pick Encrypt or Decrypt, choose the input and output files, press Start. Encrypt accepts only PNG/JPG/JPEG. Encrypted files are the raw cipher output (extension `.enc`, same size as the input, no header). Decrypt refuses any file that does not decrypt to a PNG or JPEG. Python 3 standard library only (Tkinter).

## Test
```
python -m unittest discover -s tests -t .
```
