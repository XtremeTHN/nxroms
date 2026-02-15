from enum import Enum
from dataclasses import dataclass
from ..readers import MemoryRegion

@dataclass
class KeyArea:
    aes_xts_key: bytes | None
    aes_ctr_key: bytes | None
    unk_key: bytes | None

    def __init__(self, data: bytes):
        r = MemoryRegion(data)

        self.aes_xts_key = r.read(0x20).hex()
        self.aes_ctr_key = r.read(0x10).hex()
        self.unk_key = r.read(0x10).hex()

class KeyGeneration(Enum):
    _3_0_1 = 0x03
    _4_0_0 = 0x04
    _5_0_0 = 0x05
    _6_0_0 = 0x06
    _6_2_0 = 0x07
    _7_0_0 = 0x08
    _8_1_0 = 0x09
    _9_0_0 = 0x0A
    _9_1_0 = 0x0B
    _12_1_0 = 0x0C
    _13_0_0 = 0x0D
    _14_0_0 = 0x0E
    _15_0_0 = 0x0F
    _16_0_0 = 0x10
    _17_0_0 = 0x11
    _18_0_0 = 0x12
    _19_0_0 = 0x13
    _20_0_0 = 0x14
    _21_0_0 = 0x15
    INVALID = 0xFF

    @classmethod
    def from_data(cls, data):
        try:
            return cls(data)
        except ValueError:
            return cls.INVALID

class KeyAreaEncryptionKeyIndex(Enum):
    APPLICATION = 0x00
    OCEAN = 0x01
    SYSTEM = 0x02

class KeyGenOld(Enum):
    _1_0_0 = 0x00
    UNUSED = 0x01
    _3_0_0 = 0x02

class ContentType(Enum):
    PROGRAM = 0x00
    META = 0x01
    CONTROL = 0x02
    MANUAL = 0x03
    DATA = 0x04
    PUBLIC_DATA = 0x05

class DistributionType(Enum):
    DOWNLOAD = 0x00
    GAME_CARD = 0x01