from dataclasses import dataclass

from nxroms.binary.repr import BinaryRepr

from ..binary.types import Bytes, UInt32, UInt64
from ..readers import IReadable, Readable, MemoryRegion, ReadableRegion


class InvalidHeader(Exception):
    def __init__(self, expected, got):
        super().__init__(f"Invalid header: expected {expected}, got {got}")


class PFSEntry(BinaryRepr, MemoryRegion):
    offset = UInt64(0x0)
    size = UInt64(0x8)
    string_offset = UInt32(0x10)

    name: str


class PFSItem(BinaryRepr, ReadableRegion):
    entry: PFSEntry
    data_pos: int

    def __init__(self, source: IReadable, entry: PFSEntry, data_pos: int):
        self.entry = entry
        self.data_pos = data_pos

        super().__init__(source, entry.offset + data_pos, entry.size)


class PFSHeader(BinaryRepr, Readable):
    magic = Bytes(0, 0x4)
    entry_count = UInt32(0x4)
    string_table_size = UInt32(0x8)

    entry_table: list[PFSEntry]
    _string_table: bytes

    def __init__(self, source: IReadable, magic: bytes, entry_size: int):
        super().__init__(source)

        if self.magic != magic:
            raise InvalidHeader(magic, self.magic)

        self.entry_size = entry_size

        self.entry_table = []
        self._string_table = b""

        self.entry_table_size = entry_size * self.entry_count

        str_table_offset = 0x10 + self.entry_table_size
        self._string_table = self.peek_at(str_table_offset, self.string_table_size)
        self.raw_data_pos = str_table_offset + self.string_table_size

        self._populate_entries()

    def _populate_entries(self):
        self.seek(0x10)

        for _ in range(self.entry_count):
            entry = PFSEntry(self.read(self.entry_size))
            entry.name = (
                self._string_table[entry.string_offset :].split(b"\0", 1)[0].decode()
            )
            self.entry_table.append(entry)


class PFS0(Readable):
    def __init__(self, source: IReadable, header=None):
        super().__init__(source)

        if header is None:
            header = PFSHeader(self, b"PFS0", 0x18)
        
        self.header = header

    def get_item(self, index: int) -> PFSItem:
        return PFSItem(self, self.header.entry_table[index], self.header.raw_data_pos)

    def get_items(self) -> list[PFSItem]:
        items = []
        for x in range(self.header.entry_count):
            items.append(
                PFSItem(self, self.header.entry_table[x], self.header.raw_data_pos)
            )

        return items

