from enum import Enum
from dataclasses import dataclass
from readers import MemoryRegion

@dataclass
class FsEntry:
    start_offset: int
    end_offset: int
    reserved: None = None

class FsType(Enum):
    ROM_FS=0
    PARTITION_FS=1

class HashType(Enum):
    AUTO=0
    NONE=1
    HIERARCHICAL_SHA256_HASH=2
    HIERARCHICAL_INTEGRITY_HASH=3
    AUTO_SHA3=4
    HIERARCHICAL_SHA3_256_HASH=5
    HIERARCHICAL_INTEGRITY_SHA3_HASH=6

class EncryptionType(Enum):
    AUTO=0
    NONE=1
    AES_XTS=2
    AES_CTR=3
    AES_CTR_EX=4
    AES_CTR_SKIP_LAYER_HASH=5
    AES_CTR_EX_SKIP_LAYER_HASH=6

class MetaDataHashType(Enum):
    NONE=0
    HIERARCHICAL_INTEGRITY=1


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
class FsHeader:
    VERSION = 2

    fs_type: FsType
    hash_type: HashType
    encryption_type: EncryptionType
    meta_hash_type: MetaDataHashType

    meta_hash_data_info: MetaDataHashDataInfo

    def __init__(self, data: bytes):
        r = MemoryRegion(data)

        self.fs_type = self.i(FsType, r.read_at(0x2,0x1))
        self.hash_type = self.i(HashType, r.read_at(0x3,0x1))
        self.encryption_type = self.i(EncryptionType, r.read_at(0x4,0x1))

        self.meta_hash_type = self.i(MetaDataHashType, r.read_at(0x5, 0x1))
        self.meta_hash_data_info = MetaDataHashDataInfo(r.read_at(0x1A0, 0x30))

    def i(self, en, v):
        return en(int.from_bytes(v))