from typing import TypeVar
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

T = TypeVar("Keyring")

class Keyring:
    _instance: T = None

    prod: dict

    def __init__(self, key_path=None):
        if key_path:
            self.key_file = open(key_path, "r")
        else:
            self.key_file = open(os.path.expanduser("~/.switch/prod.keys"), "r")

        self.prod = self.parse(self.key_file)
    
    def parse(self, file):
        res = {}

        for line in file.readlines():
            key, val = line.split("=")
            res[key.strip()] = val.strip()
        
        return res

    @classmethod
    def get_default(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def aes_decrypt(self, data, key, mode):
        cipher = Cipher(algorithms.AES, mode(key))
        d = cipher.decryptor()
        return d.update(data) + d.finalize()

    def get_tweak(self, sector: int) -> bytes:
        tweak = bytearray(16)
        for i in range(15, -1, -1):
            tweak[i] = sector & 0xFF
            sector >>= 8
        return bytes(tweak)
    
    def aes_xts_decrypt(
        self,
        key: str,
        src: bytes,
        length: int,
        sector: int,
        sector_size: int,
    ) -> bytes:
        if length % sector_size != 0:
            raise ValueError("Length must be multiple of sectors")

        dst = bytearray(length)

        for offset in range(0, length, sector_size):
            tweak = self.get_tweak(sector)
            sector += 1

            cipher = Cipher(
                algorithms.AES(bytes.fromhex(self.prod[key])),
                modes.XTS(tweak),
                backend=default_backend(),
            )
            decryptor = cipher.decryptor()

            dst[offset : offset + sector_size] = decryptor.update(
                src[offset : offset + sector_size]
            ) + decryptor.finalize()

        return dst