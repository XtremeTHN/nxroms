from enum import Enum
from dataclasses import dataclass
from ..readers import MemoryRegion, Readable
from ..fs.fs import FsEntry, FsHeader
from ..keys import Keyring, modes
from . import NCA_HEADER_SECTION_SIZE, NCA_HEADER_SIZE
import struct
from ..utils import media_to_bytes, is_zeroes, bytes_default


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


class InvalidNCA(Exception): ...


@dataclass
class NcaHeader(Readable):
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

    key_area: KeyArea

    def __init__(self, header: bytes):
        super().__init__(None)

        self.keyring = Keyring.get_default()
        dec = self.keyring.aes_xts_decrypt(
            "header_key", header, NCA_HEADER_SIZE, 0, NCA_HEADER_SECTION_SIZE
        )

        self.magic = dec[0x200:0x204]

        if self.magic != b"NCA3":
            raise InvalidNCA("invalid magic:", self.magic)

        self.handle_nca3(header)

        self.populate_fs_entries()
        self.populate_fs_headers()
        self.decrypt_key_area()

    def handle_nca3(self, _header: bytes):
        self.obj = MemoryRegion(
            self.keyring.aes_xts_decrypt("header_key", _header, 0xC00, 0, 0x200)
        )

        header = self.obj

        header.seek(0x204)
        self.distribution_type = DistributionType(header.read(1)[0])
        self.content_type = ContentType(header.read(1)[0])
        self.key_generation_old = KeyGenOld(header.read(1)[0])
        self.key_area_encryption_key_index = KeyAreaEncryptionKeyIndex(
            header.read(1)[0]
        )
        self.content_size = header._read_to(0x8, "<Q")
        self.program_id = header._read_to(0x8, "<Q")
        self.content_index = header._read_to(0x4, "<I")
        sdk_ver_bytes = header.read(0x4)
        self.key_generation = KeyGeneration(header.read_at(0x220, 0x1)[0])

        self.rights_id = bytes_default(header.read_at(0x230, 0x10))

        self.sdk_addon_version = (
            f"{sdk_ver_bytes[3]}.{sdk_ver_bytes[2]}.{sdk_ver_bytes[1]}.0"
        )

    def get_key_area_key(self):
        gen = self.get_key_generation()
        keys = None

        match self.key_area_encryption_key_index:
            case KeyAreaEncryptionKeyIndex.APPLICATION:
                keys = self.keyring.key_area_application
            case KeyAreaEncryptionKeyIndex.OCEAN:
                keys = self.keyring.key_area_ocean
            case KeyAreaEncryptionKeyIndex.SYSTEM:
                keys = self.keyring.key_area_system

        return keys[gen]

    def decrypt_key_area(self):
        encrypted_key_area = self.read_at(0x300, 0x40)

        if not self.rights_id:
            key = self.get_key_area_key()

            self.key_area = KeyArea(
                self.keyring.aes_decrypt(
                    encrypted_key_area, bytes.fromhex(key), modes.ECB()
                )
            )
        else:
            ...

    def get_key_generation(self) -> int:
        old = self.key_generation_old.value
        new = self.key_generation.value

        key = new if old < new else old
        return key - 1 if key > 0 else key

    def populate_fs_entries(self):
        raw_entries = MemoryRegion(self.read_at(0x240, 0x40))

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

            entries.append(FsEntry(media_to_bytes(start), media_to_bytes(end), x))

            raw_entries.read(8)

        self.fs_entries = entries

    def populate_fs_headers(self):
        headers = []
        for section in range(4):
            offset = NCA_HEADER_SIZE + (section * NCA_HEADER_SECTION_SIZE)

            data = self.read_at(offset, NCA_HEADER_SECTION_SIZE)

            # checks if this section is defined
            # if not it should be a lot of zeros
            # so i will skip that header
            if is_zeroes(data):
                continue

            headers.append(FsHeader(data, section))

        self.fs_headers = headers
