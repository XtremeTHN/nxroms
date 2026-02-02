from entry import PartitionEntry
from utils import File, Region

class Nca(Region):
    name: str
    size: int
    entry: PartitionEntry

    def __init__(self, file: File, name: str, entry: PartitionEntry, data_pos: int):
        self.entry = entry
        self.name = name
        self.size = entry.size
    
        super().__init__(file.file, entry.offset + data_pos, self.entry.size)