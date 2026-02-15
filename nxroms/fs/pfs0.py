from ..fs.entry import PartitionEntry
from ..readers import File, Region, IReadable


class FsEntry:
    start_offset: int
    end_offset: int
    reserved: int


class NotAPFS0(Exception):
    pass


class PFSItem(Region):
    name: str
    entry: PartitionEntry

    def __init__(self, file: File, name: str, entry: PartitionEntry, data_pos: int):
        self.entry = entry
        self.name = name

        super().__init__(file, entry.offset + data_pos, self.entry.size)

    def __repr__(self):
        return f"<PFSItem(name={self.name}, offset={self.offset}, end={self.end})>"


class PFS0:
    magic: str
    partition_entry_count: int
    string_table_size: int
    reserved: int

    partition_entry_table: list[PartitionEntry]
    string_table: bytes

    file_data_pos: int
    files: list[str]

    def __init__(self, source: IReadable):
        self.source = source
        self.files = []
        self.magic = self.source.read_at(0, 4)

        if self.magic != b"PFS0":
            raise NotAPFS0()

        self.populate_attrs()

    def populate_attrs(self):
        self.partition_entry_count = self.source.read_to(0x4, 0x4, "<I")
        self.string_table_size = self.source.read_to(0x8, 0x4, "<I")
        self.reserved = self.source.read_to(0xC, 0x4, "<I")

        self.partition_entry_table: list[PartitionEntry] = []

        self.source.seek(0x10)

        for _ in range(self.partition_entry_count):
            entry = PartitionEntry(self.source.read(24))
            self.partition_entry_table.append(entry)

        self.string_table = self.source.read(self.string_table_size)
        self.file_data_pos = self.source.tell()

        for x in self.partition_entry_table:
            self.files.append(
                self.string_table[x.string_offset :].split(b"\0", 1)[0].decode()
            )

    def get_file(self, index: int) -> PFSItem:
        return PFSItem(
            self.source,
            self.files[index],
            self.partition_entry_table[index],
            self.file_data_pos,
        )

    def get_files(self) -> list[PFSItem]:
        return [self.get_file(x) for x in range(self.partition_entry_count)]
