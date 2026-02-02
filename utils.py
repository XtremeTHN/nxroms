import mmap
import struct
from typing import Any
from abc import ABC, abstractmethod

class Readable(ABC):
    @abstractmethod
    def tell(self) -> int:
        ...

    @abstractmethod
    def seek(self, offset: int) -> None:
        ...
    
    @abstractmethod
    def read(self, size: int) -> bytes | None:
        ...
    
    @abstractmethod
    def read_at(self, offset: int, size: int) -> bytes:
        ...
    
    @abstractmethod
    def read_to(self, offset: int, size: int, format_string: str) -> Any:
        ...

class File(Readable):
    file: mmap.mmap
    def __init__(self, file: Readable | str):
        if isinstance(file, str):
            self._file = open(file, "rb")
            file = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)

        self.file = file

    def seek(self, offset: int):
        self.file.seek(offset)

    def tell(self) -> int:
        return self.file.tell()

    def fileno(self) -> int:
        return self.file.fileno()
    
    def read(self, size: int):
        return self.file.read(size)

    def read_at(self, offset: int, size: int):
        self.seek(offset)
        return self.file.read(size)

    def read_to(self, offset: int, size: int, format_string: str):
        return struct.unpack(format_string, self.read_at(offset, size))[0]


class OutOfBounds(Exception):
    ...

class Region(Readable):
    def __init__(self, mm: mmap.mmap, start: int, size: int):
        self._mm = mm
        self._start = start
        self._size = size
        self._pos = 0

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int) -> None:
        if not 0 <= offset <= self._size:
            raise OutOfBounds("seek out of region")
        self._pos = offset

    def read(self, size: int) -> bytes | None:
        if self._pos >= self._size:
            return None
        size = min(size, self._size - self._pos)
        data = self._mm[self._start + self._pos : self._start + self._pos + size]
        self._pos += size
        return data

    def read_at(self, offset: int, size: int) -> bytes:
        if offset + size > self._size:
            raise OutOfBounds("read out of region")
        return self._mm[self._start + offset : self._start + offset + size]

    def read_to(self, offset: int, size: int, format_string: str) -> Any:
        data = self.read_at(offset, size)
        return struct.unpack(format_string, data)

# class Region(File):
#     def __init__(self, file: Readable, offset: int, end: int):
#         super().__init__(file)
#         self.offset = offset
#         self.end = end

#     def calc_offset(self, offset: int):
#         total_offset = self.offset + offset
#         if (total_offset > self.end):
#             raise OutOfBounds(f"maximum: {self.end}, provided offset: {offset}, offset: {self.offset}")
#         return total_offset

#     def seek(self, offset):
#         super().seek(self.calc_offset(offset))
    
#     def read(self, size: int):
#         current_pos = self.file.tell() - self.offset
#         remaining_bytes = self.end - current_pos

#         if remaining_bytes <= 0:
#             return None

#         read_size = min(size, remaining_bytes)
#         return super().read(read_size)
    
#     def read_at(self, offset, size):
#         return super().read_at(self.calc_offset(offset), size)

#     def read_to(self, offset, size, format_string):
#         return super().read_to(self.calc_offset(offset), size, format_string)