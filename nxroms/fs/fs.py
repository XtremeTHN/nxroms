from nxroms.utils import media_to_bytes

from ..binary.types import (
    UInt32,
    UInt64,
    Bytes,
    Enumeration,
    DataType,
    DataTypeDescriptor,
)
from ..binary.repr import BinaryRepr
from ..readers import MemoryRegion
from enum import Enum


class FsEntry(BinaryRepr, MemoryRegion):
    start_offset = UInt32(0x0, lambda x: media_to_bytes(x))
    end_offset = UInt32(0x4, lambda x: media_to_bytes(x))
    index: int


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


class MetaDataHashDataInfo(BinaryRepr, MemoryRegion):
    table_offset = UInt64(0)
    table_size = UInt64(0x8)
    table_hash = Bytes(0x10, 0x20)


class LayerRegion(BinaryRepr, MemoryRegion):
    offset = UInt64(0)
    size = UInt64(0x8)


class HierarchicalSha256Data(BinaryRepr, MemoryRegion):
    master_hash = Bytes(0, 0x20)
    block_size = UInt32(0x20)
    layer_count = UInt32(0x24)

    def __init__(self, source: bytes):
        super().__init__(source)

        self.layer_regions = []

        self.seek(0x28)
        for x in range(self.layer_count):
            data = self.read(0x10)
            self.layer_regions.append(LayerRegion(data))


class HierarchicalIntegrityLevel(BinaryRepr, MemoryRegion):
    logical_offset = UInt64(0)
    hash_data_size = UInt64(0x8)
    block_size = UInt32(0x10)


class InfoLevelHash(BinaryRepr, MemoryRegion):
    max_layer = UInt32(0)
    salt = Bytes(0x94, 0x20)

    def __init__(self, source: bytes):
        super().__init__(source)

        self.levels = []
        self.seek(0x4)

        for x in range(6):
            data = self.read(0x18)
            self.levels.append(HierarchicalIntegrityLevel(data))


class HierarchicalIntegrity(BinaryRepr, MemoryRegion):
    magic = Bytes(0, 0x4)
    version = UInt32(0x4)
    master_hash_size = UInt32(0x8)
    info_level_hash: InfoLevelHash = Bytes(0xC, 0xB4, InfoLevelHash)

    def __init__(self, source: bytes):
        super().__init__(source)

        if self.magic != b"IVFC":
            raise ValueError(f"Invalid magic: {self.magic}")


class FsHeader(BinaryRepr, MemoryRegion):
    VERSION = 2

    fs_type: FsType = Enumeration(0x2, FsType)
    hash_type: HashType = Enumeration(0x3, HashType)

    encryption_type: EncryptionType = Enumeration(0x4, EncryptionType)

    meta_hash_type: MetaDataHashType = Enumeration(0x5, MetaDataHashType)
    meta_hash_data_info: MetaDataHashDataInfo = Bytes(0x1A0, 0x30, MetaDataHashDataInfo)

    ctr = UInt64(0x140)

    def __init__(self, source: bytes, index: int):
        super().__init__(source)

        self.index = index

        hash_data = self.read_at(0x8, 0xF8)

        if self.hash_type is HashType.HIERARCHICAL_INTEGRITY_HASH:
            self.hash_data = HierarchicalIntegrity(hash_data)
        else:
            self.hash_data = HierarchicalSha256Data(hash_data)
