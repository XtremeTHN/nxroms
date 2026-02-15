from ..readers import IReadable, Region, MemoryRegion
from dataclasses import dataclass


@dataclass
class RomFSHeader:
    header_size: int
    dir_hash_table_offset: int
    dir_hash_table_size: int
    dir_meta_table_offset: int
    dir_meta_table_size: int
    file_hash_table_offset: int
    file_hash_table_size: int
    file_meta_table_offset: int
    file_meta_table_size: int
    data_offset: int

    def __init__(self, f: IReadable):
        self.header_size = f._read_to(0x8, "<Q")
        if self.header_size > 80:
            raise ValueError("invalid header")
        self.dir_hash_table_offset = f._read_to(0x8, "<Q")
        self.dir_hash_table_size = f._read_to(0x8, "<Q")
        self.dir_meta_table_offset = f._read_to(0x8, "<Q")
        self.dir_meta_table_size = f._read_to(0x8, "<Q")
        self.file_hash_table_offset = f._read_to(0x8, "<Q")
        self.file_hash_table_size = f._read_to(0x8, "<Q")
        self.file_meta_table_offset = f._read_to(0x8, "<Q")
        self.file_meta_table_size = f._read_to(0x8, "<Q")
        self.data_offset = f._read_to(0x8, "<Q")


@dataclass
class RomFSEntry:
    parent: int
    sibling: int
    hash: int
    name_size: int
    name: str

    def __init__(self, m: MemoryRegion, padding: int):
        self.parent = m._read_to(0x4, "<I")
        self.sibling = m._read_to(0x4, "<I")

        # the final romfs entry has \xFF\xFF\xFF\xFF in the sibling field
        if self.sibling == 4294967295:
            self.sibling = None

        m.seek(m.tell() + padding)

        self.hash = m._read_to(0x4, "<I")
        self.name_size = m._read_to(0x4, "<I")
        self.name = m.read(self.name_size).decode()


@dataclass
class RomFSFile(RomFSEntry):
    offset: int
    size: int

    def __init__(self, m: MemoryRegion):
        super().__init__(m, 0x10)

        self.offset = m.read_to(0x8, 0x8, "<Q")
        self.size = m.read_to(0x10, 0x8, "<Q")


@dataclass
class RomFSDirectory(RomFSEntry):
    child: int
    file: int

    def __init__(self, m: MemoryRegion):
        super().__init__(m, 0x8)

        self.child = m.read_to(0x8, 0x4, "<I")
        self.file = m.read_to(0xC, 0x4, "<I")


# TODO: implement directory opening
@dataclass
class RomFS:
    files: list[RomFSFile]
    directories: list[RomFSDirectory]
    source: IReadable

    def __init__(self, source: IReadable):
        self.source = source

        self.header = RomFSHeader(source)
        self.files = []

        self.populate_files()

    def populate_files(self):
        sibling = 0
        while True:
            d = MemoryRegion(
                self.source.read_at(
                    self.header.file_meta_table_offset + sibling,
                    self.header.file_meta_table_size - sibling,
                )
            )
            f = RomFSFile(d)
            self.files.append(f)

            if not f.sibling:
                break

            sibling = f.sibling

    def get_file(self, file: RomFSFile) -> Region:
        data = self.source.read_at(self.header.data_offset + file.offset, file.size)
        return MemoryRegion(data)

    def populate(self): ...
