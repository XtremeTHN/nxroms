from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class Crypto:
    @staticmethod
    def get_decryptor(key: bytes, mode: object, algorithm=algorithms.AES):
        cipher = Cipher(algorithm(key), mode)
        return cipher.decryptor()

    @staticmethod
    def aes_decrypt(data: bytes, key: bytes, mode: object) -> bytes:
        d = Crypto.get_decryptor(key, mode)
        return d.update(data) + d.finalize()

    @staticmethod
    def get_tweak(sector: int) -> bytes:
        return int.to_bytes(sector, length=16, byteorder="big")

    @staticmethod
    def aes_xts_decrypt(
        key: str, src: bytes, length: int, sector: int, sector_size: int
    ) -> bytes:
        if length % sector_size != 0:
            raise ValueError("Length must be multiple of sectors")

        dst = bytes()

        for offset in range(0, length, sector_size):
            tweak = Crypto.get_tweak(sector)
            sector += 1

            dst += Crypto.aes_decrypt(
                src[offset : offset + sector_size],
                bytes.fromhex(key),
                modes.XTS(tweak),
            )

        return dst
