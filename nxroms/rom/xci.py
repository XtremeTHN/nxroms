from nxroms.fs.pfs0 import NotAPFS0, PFSHeader
from ..readers import MemoryRegion, IReadable, Region
from .rom import Rom
from dataclasses import dataclass
from enum import Enum
from ..utils import media_to_bytes


class CardSize(Enum):
    _1GB = 0xFA
    _2GB = 0xF8
    _4GB = 0xF0
    _8GB = 0xE0
    _16GB = 0xE1
    _32GB = 0xE2


class NotXci(Exception):
    pass


@dataclass
class EHeader:
    magic = "HEAD"
    rom_area_start_page_address: int  # media bytes
    backup_area_start_page_address = 0xFFFFFFFF
    titlekey_dec_index: int
    rom_size: CardSize
    version: int

    partition_fs_header_address: int
    partition_fs_header_size: int

    def __init__(self, data: bytes):
        d = MemoryRegion(data)

        d.seek(0x100)
        if (n := d.read(4)) != b"HEAD":
            raise NotXci(f"invalid magic: {n}")
        else:
            print(n)

        self.rom_area_start_page_address = media_to_bytes(d.read_to(0x104, 0x4, "<I"))
        self.titlekey_dec_index = d.read_at(0x10C, 0x1)[0]
        self.rom_size = CardSize(d.read_at(0x10D, 0x1)[0])
        self.version = d.read_at(0x10E, 0x1)[0]

        self.partition_fs_header_address = d.read_to(0x130, 0x8, "<Q")
        self.partition_fs_header_size = d.read_to(0x138, 0x8, "<Q")


@dataclass
class Header:
    magic = "HEAD"
    rom_area_start_page_address: int  # media bytes
    backup_area_start_page_address = 0xFFFFFFFF
    titlekey_dec_index: int
    rom_size: CardSize
    version: int

    partition_fs_header_address: int
    partition_fs_header_size: int

    def __init__(self, data: bytes): ...


class Xci(Rom):
    def __init__(self, file: IReadable | str):
        super().__init__(file)

        self.header = Header(self.read_at(0, 0x200))

        # r = Region(file, 0xF000)
        # self.pfs = PFSHeader(r, b"HFS0", 0x20)
