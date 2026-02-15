from ..fs.entry import PartitionEntry
from ..readers import File, MemoryRegion, EncryptedCtrRegion
from ..fs.fs import FsEntry, FsHeader, FsType, InvalidFs, EncryptionType, HashType
from ..fs.pfs0 import PFSItem, PFS0
from ..fs.romfs import RomFS
from ..utils import media_to_bytes, bytes_default, is_zeroes

from .header import DistributionType, ContentType, KeyGenOld, KeyAreaEncryptionKeyIndex, KeyGeneration, KeyArea
from ..keys import Keyring, modes
import struct


class InvalidNCA(Exception):
    ...

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

    key_area: KeyArea

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
        self.decrypt_key_area()
    
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
        encrypted_key_area = self.decrypted_header.read_at(0x300, 0x40)

        if not self.rights_id:
            key = self.get_key_area_key()

            self.key_area = KeyArea(
                self.keyring.aes_decrypt(encrypted_key_area, bytes.fromhex(key), modes.ECB())
            )
        else:
            ...

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
                    media_to_bytes(start),
                    media_to_bytes(end),
                    x
                )
            )

            raw_entries.read(8)

        self.fs_entries = entries
    
    def populate_fs_headers(self):
        headers = []
        for section in range(4):
            offset = NCA_HEADER_SIZE + (section * NCA_HEADER_SECTION_SIZE)

            data = self.decrypted_header.read_at(offset, NCA_HEADER_SECTION_SIZE)
            
            # checks if this section is defined
            # if not it should be a lot of zeros
            # so i will skip that header
            if is_zeroes(data):
                continue
            
            headers.append(
                FsHeader(
                    data,
                    section
                )
            )

        self.fs_headers = headers

    def get_entry_for_header(self, header: FsHeader):
        return [x for x in self.fs_entries if x.index == header.index][0]
    
    def open_fs(self, header: FsHeader):
        def get_enc_region(offset, end_offset):
            key = bytes.fromhex(self.key_area.aes_ctr_key)
            return EncryptedCtrRegion(self, offset, end_offset, key, header.ctr)
        
        entry = self.get_entry_for_header(header)
        
        if header.encryption_type != EncryptionType.AES_CTR:
            raise Exception("Only aes ctr encryption is supported", header.encryption_type)
        
        fs_offset = 0
        match header.hash_type:
            case HashType.HIERARCHICAL_INTEGRITY_HASH:
                fs_offset = entry.start_offset + header.hash_data.info_level_hash.levels[-1].logical_offset
            case HashType.HIERARCHICAL_SHA256_HASH:
                fs_offset = entry.start_offset + header.hash_data.layer_regions[1].offset
            case _:
                raise Exception("invalid hash type")
        
        return get_enc_region(fs_offset, entry.end_offset)
    
    def open_pfs(self, header: FsHeader):
        if header.fs_type != FsType.PARTITION_FS:
            raise InvalidFs(FsType.PARTITION_FS, header.fs_type)

        fs = self.open_fs(header)
        return PFS0(fs)
    
    def open_romfs(self, header: FsHeader):
        if header.fs_type != FsType.ROM_FS:
            raise InvalidFs(FsType.ROM_FS, header.fs_type)

        return RomFS(self.open_fs(header))
        
    def get_key_generation(self) -> int:
        old = self.key_generation_old.value
        new = self.key_generation.value

        key = new if old < new else old
        return key - 1 if key > 0 else key

    def handle_nca3(self, _header: bytes):
        self.decrypted_header = MemoryRegion(self.keyring.aes_xts_decrypt("header_key", _header, 0xC00, 0, 0x200))
        header = self.decrypted_header

        self.distribution_type = DistributionType(int.from_bytes(header.read_at(0x204, 1)))
        self.content_type = ContentType(int.from_bytes(header.read_at(0x205, 0x1)))
        self.key_generation_old = KeyGenOld(int.from_bytes(header.read_at(0x206, 0x1)))
        self.key_area_encryption_key_index = KeyAreaEncryptionKeyIndex(int.from_bytes(header.read_at(0x207, 0x1)))
        self.key_generation = KeyGeneration(int.from_bytes(header.read_at(0x220, 0x1)))

        self.rights_id = bytes_default(header.read_at(0x230, 0x10))

        self.content_size = header.read_to(0x208, 0x8, "<Q")
        self.program_id = header.read_to(0x210, 0x8, "<q")
        self.content_index = header.read_to(0x218, 0x4, "<I")

        sdk_ver_bytes = header.read_at(0x21C, 0x4)
        self.sdk_addon_version = f"{sdk_ver_bytes[3]}.{sdk_ver_bytes[2]}.{sdk_ver_bytes[1]}.0"


    # TODO: make a constructor that takes a file and parse it

    def __repr__(self):
        return f"<Nca(name={self.name}, offset={self.offset}, end={self.end})>"