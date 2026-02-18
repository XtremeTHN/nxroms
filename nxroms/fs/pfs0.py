from ..fs.entry import PartitionEntry
from ..readers import File, Readable, Region, IReadable
from dataclasses import dataclass


class FsEntry:
    start_offset: int
    end_offset: int
    reserved: int


class NotAPFS0(Exception):
    pass


@dataclass
class PFSEntry:
    offset: int
    size: int
    name: str


@dataclass
class PFSHeader:
    magic: str
    file_count: int
    string_table_size: int
    file_entry_table: list
    string_table: bytes
    raw_data_pos: int

    def __init__(self, obj: IReadable, magic: bytes, entry_size: int):
        self.obj = obj

        if (n := self.obj.read(4)) != magic:
            raise NotAPFS0(f"invalid magic: {n}")

        self.file_count = obj.read_to(0x4, 0x4, "<I")
        self.string_table_size = obj.read_to(0x8, 0x4, "<I")
        self.file_entry_table = []

        self.entry_size = entry_size
        str_table_offset = 0x10 + entry_size * self.file_count
        self.string_table = obj.read_at(str_table_offset, self.string_table_size)
        self.raw_data_pos = str_table_offset + self.string_table_size

        self.populate_entries()

    def populate_entries(self):
        self.obj.seek(0x10)
        for _ in range(self.file_count):
            offset = self.obj.read_unpack(0x8, "<Q")
            size = self.obj.read_unpack(0x8, "<Q")
            name_offset = self.obj.read_unpack(0x4, "<I")
            name = self.string_table[name_offset:].split(b"\0", 1)[0].decode()

            # get the remaining bytes and skip them
            # this is to use the same class for HFS0 and PFS0
            self.obj.skip(self.entry_size - 0x14)

            self.file_entry_table.append(PFSEntry(offset, size, name))


@dataclass
class PFSItem(Region):
    entry: PartitionEntry
    data_pos: int

    def __init__(self, file: File, entry: PFSEntry, data_pos: int):
        self.entry = entry
        super().__init__(file, entry.offset + data_pos, self.entry.size)


class PFS0(Readable):
    header: PFSHeader
    files: list[str]

    def __init__(self, source: IReadable):
        super().__init__(source)

        self.header = PFSHeader(source, b"PFS0", 0x18)

    def get_file(self, index: int) -> PFSItem:
        return PFSItem(
            self.source, self.header.file_entry_table[index], self.header.raw_data_pos
        )

    def get_files(self) -> list[PFSItem]:
        return [self.get_file(x) for x in range(self.partition_entry_count)]
