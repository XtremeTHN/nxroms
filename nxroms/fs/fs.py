from enum import Enum
from dataclasses import dataclass
from ..readers import MemoryRegion
from ..utils import is_zeroes
import struct


@dataclass
class FsEntry:
    start_offset: int
    end_offset: int
    index: int
    reserved: None = None


class FsType(Enum):
    ROM_FS = 0
    PARTITION_FS = 1


class HashType(Enum):
    AUTO = 0
    HIERARCHICAL_SHA256_HASH = 2
    HIERARCHICAL_INTEGRITY_HASH = 3


class EncryptionType(Enum):
    AUTO = 0
    NONE = 1
    AES_XTS = 2
    AES_CTR = 3
    AES_CTR_EX = 4
    AES_CTR_SKIP_LAYER_HASH = 5
    AES_CTR_EX_SKIP_LAYER_HASH = 6


class MetaDataHashType(Enum):
    NONE = 0
    HIERARCHICAL_INTEGRITY = 1


@dataclass
class MetaDataHashDataInfo:
    table_offset: int
    table_size: int
    table_hash: bytes | None

    def __init__(self, data: bytes):
        r = MemoryRegion(data)

        self.table_offset = r.read_to(0, 0x8, "<Q")
        self.table_size = r.read_to(0x8, 0x8, "<Q")

        hash = r.read_at(0x10, 0x20)
        if not any(hash):
            self.table_hash = None
        else:
            self.table_hash = hash


@dataclass
class LayerRegion:
    offset: int
    size: int


@dataclass
class HierarchicalSha256Data:
    master_hash: bytes
    block_size: int
    layer_count = 2
    layer_regions: list[LayerRegion]

    def __init__(self, data: bytes):
        r = MemoryRegion(data)

        self.master_hash = r.read_at(0, 0x20)
        self.block_size = r.read_to(0x20, 0x4, "<I")
        self.layer_count = r.read_to(0x24, 0x4, "<I")
        self.layer_regions = []

        r.seek(0x28)
        for x in range(self.layer_count):
            offset = struct.unpack("<Q", r.read(0x8))[0]
            size = struct.unpack("<Q", r.read(0x8))[0]
            layer = LayerRegion(offset, size)
            self.layer_regions.append(layer)


@dataclass
class HierarchicalIntegrityLevelInfo:
    offset: int
    size: int
    block_size_log2: int
    reserved = None


# TODO: if the romfs is invalid, check this class
# the levels data are rare
@dataclass
class HierarchicalIntegrityLevel:
    logical_offset: int
    hash_data_size: int
    block_size: int
    reserved = None

    def __init__(self, data: bytes):
        r = MemoryRegion(data)

        self.logical_offset = r.read_to(0x0, 0x8, "<Q")
        self.hash_data_size = r.read_to(0x8, 0x8, "<Q")
        self.block_size = r.read_to(0x10, 0x4, "<I")


@dataclass
class InfoLevelHash:
    max_layers: int
    levels: list[HierarchicalIntegrityLevel]
    salt: bytes

    def __init__(self, data: bytes):
        r = MemoryRegion(data)
        self.max_layers = r.read_to(0x0, 0x4, "<I")
        self.levels = []

        r.seek(0x4)
        for x in range(6):
            data = r.read(0x18)
            self.levels.append(HierarchicalIntegrityLevel(data))

        salt = r.read_at(0x94, 0x20)
        if is_zeroes(salt):
            self.salt = None
        else:
            self.salt = salt


@dataclass
class HierarchicalIntegrity:
    magic = b"IVFC"
    version: int
    master_hash_size: int
    info_level_hash: InfoLevelHash

    def __init__(self, data: bytes):
        r = MemoryRegion(data)

        if r.read_at(0x0, 0x4) != b"IVFC":
            raise ValueError("Invalid magic")

        self.version = r.read_to(0x4, 0x4, "<I")
        self.master_hash_size = r.read_to(0x8, 0x4, "<I")
        self.info_level_hash = InfoLevelHash(r.read_at(0xC, 0xB4))


@dataclass
class FsHeader:
    VERSION = 2

    fs_type: FsType
    hash_type: HashType
    hash_data: HierarchicalIntegrity | HierarchicalSha256Data
    encryption_type: EncryptionType

    meta_hash_type: MetaDataHashType
    meta_hash_data_info: MetaDataHashDataInfo
    ctr: bytes
    index: int

    def __init__(self, data: bytes, index: int):
        r = MemoryRegion(data)
        self.index = index

        self.fs_type = self.i(FsType, r.read_at(0x2, 0x1))
        self.hash_type = self.i(HashType, r.read_at(0x3, 0x1))
        self.encryption_type = self.i(EncryptionType, r.read_at(0x4, 0x1))

        self.meta_hash_type = self.i(MetaDataHashType, r.read_at(0x5, 0x1))
        self.meta_hash_data_info = MetaDataHashDataInfo(r.read_at(0x1A0, 0x30))
        self.ctr = r.read_to(0x140, 0x8, "<Q")

        hash_data = r.read_at(0x8, 0xF8)
        if self.hash_type is HashType.HIERARCHICAL_INTEGRITY_HASH:
            self.hash_data = HierarchicalIntegrity(hash_data)
        else:
            self.hash_data = HierarchicalSha256Data(hash_data)

    def i(self, en, v):
        return en(int.from_bytes(v))


class InvalidFs(Exception):
    def __init__(self, expected, given):
        super().__init__(f"Invalid filesystem: expected {expected}, given {given}")
