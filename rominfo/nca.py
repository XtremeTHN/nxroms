from fs.entry import PartitionEntry
from readers import File, MemoryRegion, Region
from fs.fs import FsEntry, FsHeader
from fs.pfs0 import PFSItem
from enum import Enum

from keys import Keyring
import struct


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

NCA_HEADER_SIZE = 0x400
NCA_ENCRYPTED_SIZE = 0xC00
NCA_HEADER_SECTION_SIZE = 0x200

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
    key_generation: KeyGeneration
    rights_id: str

    magic: str

    fs_entries: list[FsEntry]
    fs_headers: list[FsHeader]
    decrypted_header: MemoryRegion

    key_area: list[str]

    def __init__(self, file: File, name: str, entry: PartitionEntry, data_pos: int):
        super().__init__(file, name, entry, data_pos)
        self.end += entry.offset

        self.keyring = Keyring.get_default()
        
        header = self.read_at(0, 0xC00)
        dec = self.keyring.aes_xts_decrypt("header_key", header, NCA_HEADER_SIZE, 0, NCA_HEADER_SECTION_SIZE)

        self.magic = dec[0x200:0x204]

        match self.magic:
            case b"NCA3":
                self.handle_nca3(header)
            case _:
                raise InvalidNCA("invalid magic:", self.magic)
        
        self.populate_fs_entries()
        self.populate_fs_headers()

    def populate_fs_entries(self):
        raw_entries = MemoryRegion(self.decrypted_header.read_at(0x240, 0x40))

        entries = []

        for x in range(4):
            start = raw_entries.read(4)
            end = raw_entries.read(4)

            if len(start) == 0 and len(end) == 0:
                print("invalid values")
                continue

            start = struct.unpack("<I", start)[0]
            end = struct.unpack("<I", end)[0]

            if start == 0 and end == 0:
                continue

            entries.append (
                FsEntry(
                    start,
                    end
                )
            )

            raw_entries.read(8)

        self.fs_entries = entries
    
    def populate_fs_headers(self):
        headers = []
        for section in range(4):
            offset = NCA_HEADER_SIZE + (section * NCA_HEADER_SECTION_SIZE)

            headers.append(
                FsHeader(
                    self.decrypted_header.read_at(offset, NCA_HEADER_SECTION_SIZE)
                )
            )

        self.fs_headers = headers
    
    def get_key_generation(self):
        old = self.key_generation_old.value
        new = self.key_generation.value

        key = old if old < new else new
        return key - 1 if key > 0 else key

    def handle_nca3(self, _header: bytes):
        self.decrypted_header = MemoryRegion(self.keyring.aes_xts_decrypt("header_key", _header, 0xC00, 0, 0x200))
        open("out.bin", "wb").write(self.decrypted_header.source)

        header = self.decrypted_header

        self.distribution_type = DistributionType(int.from_bytes(header.read_at(0x204, 1)))
        self.content_type = ContentType(int.from_bytes(header.read_at(0x205, 0x1)))
        self.key_generation_old = KeyGenOld(int.from_bytes(header.read_at(0x206, 0x1)))
        self.key_area_encryption_key_index = KeyAreaEncryptionKeyIndex(int.from_bytes(header.read_at(0x207, 0x1)))
        self.key_generation = KeyGeneration(int.from_bytes(header.read_at(0x220, 0x1)))

        self.content_size = header.read_to(0x208, 0x8, "<Q")
        self.program_id = header.read_to(0x210, 0x8, "<q")
        self.content_index = header.read_to(0x218, 0x4, "<I")

        sdk_ver_bytes = header.read_at(0x21C, 0x4)
        self.sdk_addon_version = f"{sdk_ver_bytes[3]}.{sdk_ver_bytes[2]}.{sdk_ver_bytes[1]}.0"


    # TODO: make a constructor that takes a file and parse it

    def __repr__(self):
        return f"<Nca(name={self.name}, offset={self.offset}, end={self.end})>"