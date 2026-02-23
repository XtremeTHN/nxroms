from enum import Enum
from dataclasses import dataclass

from nxroms.fs.pfs0 import PFSHeader
from ..utils import media_to_bytes
from ..binary.repr import BinaryRepr
from ..binary.types import UInt32, UInt64, Bytes, Enumeration
from ..readers import MemoryRegion, IReadable, Readable, ReadableRegion


class NotXci(Exception):
    pass


class CardSize(Enum):
    _1GB = 0xFA
    _2GB = 0xF8
    _4GB = 0xF0
    _8GB = 0xE0
    _16GB = 0xE1
    _32GB = 0xE2


class XciHeader(BinaryRepr, MemoryRegion):
    magic = Bytes(0x100, 0x4)
    rom_area_start_page_address = UInt32(0x104, media_to_bytes)
    title_key_dec_index = Bytes(0x10C, 0x1, lambda x: x[0])
    rom_size = Enumeration(0x10D, CardSize)
    version = Bytes(0x10E, 0x1, lambda x: x[0])

    hfs_header_offset = UInt64(0x130)
    hfs_header_size = UInt64(0x138)

    def __init__(self, source: bytes):
        super().__init__(source)

        if self.magic != b"HEAD":
            raise NotXci(f"Invalid magic: {self.magic}")


class Xci(Readable):
    header: XciHeader = Bytes(0x0, 0x200, XciHeader)

    def __init__(self, source: IReadable | str):
        super().__init__(source)

        reader = MemoryRegion(
            self.peek_at(self.header.hfs_header_offset, self.header.hfs_header_size)
        )

        self.hfs_header = PFSHeader(reader, b"HFS0", 0x40)
