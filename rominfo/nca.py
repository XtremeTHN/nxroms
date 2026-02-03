from entry import PartitionEntry
from readers import File, MemoryRegion
from fs import PFSItem
from enum import Enum

from keys import Keyring



class InvalidNCA(Exception):
    ...

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

class Nca(PFSItem):
    name: str
    entry: PartitionEntry

    distribution_type: DistributionType
    content_type: ContentType
    key_generation_old: KeyGenOld
    key_area_encryption_key_index = KeyAreaEncryptionKeyIndex

    content_size: int
    program_id: int
    content_index: int
    sdk_addon_version: str
    rights_id: str

    magic: str

    def __init__(self, file: File, name: str, entry: PartitionEntry, data_pos: int):
        super().__init__(file, name, entry, data_pos)
        self.end += entry.offset

        self.keyring = Keyring.get_default()
        
        header = self.read_at(0, 0xC00)
        self.decrypted_header = MemoryRegion(self.keyring.aes_xts_decrypt("header_key", header, 0x400, 0, 0x200))

        self.magic = self.decrypted_header.read_at(0x200, 0x4)

        if self.magic.startswith(b"NCA") is False:
            print("warn: invalid nca magic:", self.magic)
            return
        
        self.distribution_type = DistributionType(int.from_bytes(self.decrypted_header.read_at(0x204, 1)))
        self.content_type = ContentType(int.from_bytes(self.decrypted_header.read_at(0x205, 0x1)))
        self.key_generation_old = KeyGenOld(int.from_bytes(self.decrypted_header.read_at(0x206, 0x1)))
        self.key_area_encryption_key_index = KeyAreaEncryptionKeyIndex(int.from_bytes(self.decrypted_header.read_at(0x207, 0x1)))

        self.content_size = self.decrypted_header.read_to(0x208, 0x8, "<Q")
        self.program_id = self.decrypted_header.read_to(0x210, 0x8, "<q")
        self.content_index = self.decrypted_header.read_to(0x218, 0x4, "<I")

        sdk_ver_bytes = self.decrypted_header.read_at(0x21C, 0x4)
        self.sdk_addon_version = f"{sdk_ver_bytes[3]}.{sdk_ver_bytes[2]}.{sdk_ver_bytes[1]}.0"

    # TODO: make a constructor that takes a file and parse it

    def __repr__(self):
        return f"<Nca(name={self.name}, offset={self.offset}, end={self.end})>"