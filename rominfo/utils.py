from enum import Enum

class ByteEnum(Enum):
    def __init__(self, value):
        super().__init__(int.from_bytes(value))


def media_to_bytes(media):
    return media * 0x200

def is_zeroes(data: bytes):
    return not any(data)