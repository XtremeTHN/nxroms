from ..binary.repr import BinaryRepr
from ..binary.types import UInt32, UInt64
from ..readers import MemoryRegion, ReadableRegion, Readable, IReadable


class RomFSHeader(BinaryRepr, MemoryRegion):
    header_size = UInt64(0)

    dir_hash_table_offset = UInt64(0x8)
    dir_hash_table_size = UInt64(0x10)

    dir_meta_table_offset = UInt64(0x18)
    dir_meta_table_size = UInt64(0x20)

    file_hash_table_offset = UInt64(0x28)
    file_hash_table_size = UInt64(0x30)

    file_meta_table_offset = UInt64(0x38)
    file_meta_table_size = UInt64(0x40)

    data_offset = UInt64(0x48)

    def __init__(self, source: bytes):
        super().__init__(source)

        if self.header_size > 80:
            raise ValueError(f"Invalid XCI header, size: {self.header_size}")


class RomFSEntry(BinaryRepr, MemoryRegion):
    parent = UInt32(0)

    # the final romfs entry has \xFF\xFF\xFF\xFF in the sibling field
    sibling = UInt32(0x4, lambda x: None if x == 4294967295 else x)

    def __init__(self, source: bytes, padding: int):
        super().__init__(source)

        self.skip(padding)

        self.hash = self.read_unpack(0x4, "<I")
        self.name_size = self.read_unpack(0x4, "<I")
        self.name = self.read(self.name_size).decode()


class RomFSFile(RomFSEntry):
    offset = UInt64(0x8)
    size = UInt64(0x10)

    def __init__(self, source: bytes):
        super().__init__(source, 0x10)


class RomFSDirectory(RomFSEntry):
    child = UInt32(0x8)
    file = UInt32(0xC)

    def __init__(self, source: bytes):
        super().__init__(source, 0x8)


class RomFS(Readable):
    def __init__(self, source: IReadable):
        super().__init__(source)
        self.files: list[RomFSFile] = []

        self.header = RomFSHeader(source.peek_at(0, 0x50))
        self.populate_files()

    def populate_files(self):
        sibling = 0
        while True:
            d = self.source.peek_at(
                self.header.file_meta_table_offset + sibling,
                self.header.file_meta_table_size - sibling,
            )
            f = RomFSFile(d)
            self.files.append(f)

            if not f.sibling:
                break

            sibling = f.sibling

    def get_file(self, file: RomFSFile) -> ReadableRegion:
        return ReadableRegion(self, self.header.data_offset + file.offset, file.size)
