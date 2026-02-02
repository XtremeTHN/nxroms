import struct
from nca import Nca
from utils import File
from entry import PartitionEntry

class NotAPFS0(Exception):
    pass


class PFS0:
    magic: str
    partition_entry_count: int
    string_table_size: int
    reserved: int

    partition_entry_table: list[PartitionEntry]
    string_table: bytes

    file_data_pos: int
    files: list[str]

    def __init__(self, file: str):
        self.file = File(file)
        self.files = []
        self.magic = self.file.read_at(0, 4)
        
        if self.magic != b"PFS0":
            raise NotAPFS0()
        
        self.populate_attrs()

    def populate_attrs(self):
        self.partition_entry_count = self.file.read_to(0x4, 0x4, "<I")
        self.string_table_size = self.file.read_to(0x8, 0x4, "<I")
        self.reserved = self.file.read_to(0xC, 0x4, "<I")

        self.partition_entry_table: list[PartitionEntry] = []

        self.file.seek(0x10)

        for _ in range(self.partition_entry_count):
            entry = PartitionEntry(self.file.read(24))
            self.partition_entry_table.append(entry)
                
        self.string_table = self.file.read(self.string_table_size)
        self.file_data_pos = self.file.tell()

        for x in self.partition_entry_table:
            self.files.append(self.string_table[x.string_offset:].split(b"\0", 1)[0].decode())
    
    def get_nca(self, index: int) -> Nca:
        return Nca(self.file, self.files[index], self.partition_entry_table[index], self.file_data_pos)

    def get_ncas(self) -> list[Nca]:
        return [self.get_nca(x) for x in range(self.partition_entry_count)]
    
p = PFS0("undertale.nsp")
p.populate_attrs()

print(
    "partition_entry_count:", p.partition_entry_count,
    "string_table_size:", p.string_table_size,
    "reserved:", p.reserved
)

for x in p.get_ncas():
    print(x.name, x.size)
    n = open(f"out/{x.name}", "wb")
    
    while True:
        chunk = x.read(1024)
        if not chunk:
            print("end", x.entry.offset, x.size, x.tell())
            break

        n.write(chunk)