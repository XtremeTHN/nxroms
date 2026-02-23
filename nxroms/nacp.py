from nxroms.readers import Readable, MemoryRegion
from nxroms.fs.pfs0 import IReadable
from .binary.repr import BinaryRepr
from .binary.types import Bytes
from enum import Enum


def strip(string: bytes) -> str:
    return string.replace(b"\x00", b"").decode()


class TitleLanguage(Enum):
    AMERICAN_ENGLISH = 0
    BRITISH_ENGLISH = 1
    JAPANESE = 2
    FRENCH = 3
    GERMAN = 4
    LATIN_AMERICAN_SPANISH = 5
    SPANISH = 6
    ITALIAN = 7
    DUTCH = 8
    CANADIAN_FRENCH = 9
    PORTUGUESE = 10
    RUSSIAN = 11
    KOREAN = 12
    TRADITIONAL_CHINESE = 13
    SIMPLIFIED_CHINESE = 14
    BRAZILIAN_PORTUGUESE = 15


class Title(BinaryRepr, MemoryRegion):
    name = Bytes(0, 0x200, lambda x: strip(x))
    publisher = Bytes(0x200, 0x100, lambda x: strip(x))

    def __init__(self, source: bytes, index: int):
        self.language = index
        super().__init__(source)


class Nacp(Readable):
    version = Bytes(0x3060, 0x10, lambda x: strip(x))

    def __init__(self, source: IReadable):
        super().__init__(source)

        self.titles: list[Title] = []

        orig = self.tell()

        for x in range(16):
            t = Title(self.read(0x300), x)

            if t.name == "" or t.publisher == "":
                continue
            self.titles.append(t)
        self.seek(orig)
