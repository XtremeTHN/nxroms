import struct

class PartitionEntry:
    offset: int
    size: int
    string_offset: int
    reserved: int

    def __init__(self, data: bytes):
        # print(len(data), data)
        self.offset, self.size, self.string_offset, self.reserved = struct.unpack("<QQII", data)