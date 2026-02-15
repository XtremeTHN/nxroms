from typing import TypeVar
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from io import BufferedReader

T = TypeVar("Keyring")


class Keyring:
    _instance: T = None

    prod: dict
    key_area_application: list[str] = []
    key_area_ocean: list[str] = []
    key_area_system: list = []

    def __init__(self, key_path=None):
        if key_path:
            self.key_file = open(key_path, "r")
        else:
            self.key_file = open(os.path.expanduser("~/.switch/prod.keys"), "r")

        self.prod = self.parse(self.key_file)

    def parse(self, file: BufferedReader):
        res = {}

        for line in file.readlines():
            key, val = line.split("=")

            if key.startswith("key_area_key_application_"):
                self.key_area_application.append(val)
                continue

            if key.startswith("key_area_key_ocean_"):
                self.key_area_ocean.append(val)
                continue

            if key.startswith("key_area_key_system_"):
                self.key_area_system.append(val)
                continue

            res[key.strip()] = val.strip()

        return res

    @classmethod
    def get_default(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # TODO: move this method to another class
    def aes_decrypt(self, data, key, mode):
        d = self.get_decryptor(key, mode)
        return d.update(data) + d.finalize()

    # TODO: move this method to another class
    @staticmethod
    def get_decryptor(key, mode, algorithm=algorithms.AES):
        cipher = Cipher(algorithm(key), mode)
        return cipher.decryptor()

    # TODO: move this method to another class
    @staticmethod
    def get_tweak(sector: int) -> bytes:
        return int.to_bytes(sector, length=16, byteorder="big")

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

        dst = bytes()

        for offset in range(0, length, sector_size):
            tweak = Keyring.get_tweak(sector)
            sector += 1

            dst += self.aes_decrypt(
                src[offset : offset + sector_size],
                bytes.fromhex(self.prod[key]),
                modes.XTS(tweak),
            )

        return dst
