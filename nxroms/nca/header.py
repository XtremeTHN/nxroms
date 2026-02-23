from enum import Enum

from nxroms.utils import is_all_zero
from ..keyring import Keyring
from ..crypto import Crypto, modes
from ..binary.repr import BinaryRepr
from ..fs.fs import FsEntry, FsHeader
from ..readers import MemoryRegion
from ..binary.types import Enumeration, Bytes, UInt32, UInt64

NCA_HEADER_SIZE = 0x400
NCA_ENCRYPTED_SIZE = 0xC00
NCA_HEADER_SECTION_SIZE = 0x200


class KeyArea(BinaryRepr, MemoryRegion):
    aes_xts_key = Bytes(0, 0x20, _class=lambda x: x.hex())
    aes_ctr_key = Bytes(0x20, 0x10, _class=lambda x: x.hex())
    unk_key = Bytes(0x30, 0x10, _class=lambda x: x.hex())


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


class NcaHeader(BinaryRepr, MemoryRegion):
    distribution_type: DistributionType = Enumeration(0x204, DistributionType)
    content_type: ContentType = Enumeration(0x205, ContentType)
    key_generation_old: KeyGenOld = Enumeration(0x206, KeyGenOld)
    key_area_encryption_key_index = Enumeration(0x207, KeyAreaEncryptionKeyIndex)

    content_size = UInt64(0x208)
    program_id = UInt64(0x210)
    content_index = UInt32(0x218)
    sdk_addon_version = Bytes(0x21C, 0x4, lambda x: f"{x[3]}.{x[2]}.{x[1]}.0")

    key_generation = Bytes(0x220, 0x1, lambda x: x[0])

    rights_id = Bytes(0x230, 0x10)

    def __init__(self, source: bytes):
        self.keyring = Keyring.get_default()

        dec = Crypto.aes_xts_decrypt(
            self.keyring.prod["header_key"],
            source,
            NCA_ENCRYPTED_SIZE,
            0,
            NCA_HEADER_SECTION_SIZE,
        )

        self.magic = dec[0x200:0x204]
        if self.magic != b"NCA3":
            raise InvalidNCA(f"Invalid magic: {self.magic}")

        self.fs_entries: list[FsEntry] = []
        self.fs_headers: list[FsHeader] = []

        super().__init__(dec)

        self.decrypt_key_area()
        self.populate_fs_entries()
        self.populate_fs_headers()

    def get_key_generation(self) -> int:
        old = self.key_generation_old.value
        new = self.key_generation

        key = new if old < new else old
        return key - 1 if key > 0 else key

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
        encrypted_key_area = self.peek_at(0x300, 0x40)

        if not self.rights_id:
            key = self.get_key_area_key()

            self.key_area = KeyArea(
                Crypto.aes_decrypt(encrypted_key_area, bytes.fromhex(key), modes.ECB())
            )
        else:
            # TODO: implement decryption of rights id
            ...

    def populate_fs_entries(self):
        raw_entries = MemoryRegion(self.peek_at(0x240, 0x40))

        self.fs_entries = []

        for x in range(4):
            entry = FsEntry(raw_entries.read(0x10))

            if entry.start_offset == 0 and entry.end_offset == 0:
                continue

            self.fs_entries.append(entry)

    def populate_fs_headers(self):
        headers = []
        for section in range(4):
            offset = NCA_HEADER_SIZE + (section * NCA_HEADER_SECTION_SIZE)

            data = self.peek_at(offset, NCA_HEADER_SECTION_SIZE)

            # checks if this section is defined
            # if not it should be a lot of zeros
            # so we will skip that header
            if is_all_zero(data):
                continue

            headers.append(FsHeader(data, section))

        self.fs_headers = headers
