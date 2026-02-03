import mmap
import struct
from typing import Any
from io import BufferedReader
from abc import ABC, abstractmethod

class IReadable(ABC):
    @abstractmethod
    def tell(self) -> int:
        """
        Gets the cursor position
        
        Returns:
            int: The cursor position
        """
        ...

    @abstractmethod
    def seek(self, offset: int) -> None:
        """
        Moves the cursor to offset
        
        Args:
            offset (int): The cursor position
        """
        ...
    
    @abstractmethod
    def read(self, size: int) -> bytes | None:
        """
        Reads up to `size` bytes from the source.

        Args:
            size (int): The maximum number of bytes to read.

        Returns:
            bytes | None: The bytes read from the source, or None if no more data is available.
        """
        ...
    
    @abstractmethod
    def read_at(self, offset: int, size: int) -> bytes:
        """
        Reads a sequence of bytes from the given offset.

        Args:
            offset (int): The position in the data source to start reading from.
            size (int): The number of bytes to read.

        Returns:
            bytes: The bytes read from the specified offset and size.
        """
        ...
    
    @abstractmethod
    def read_to(self, offset: int, size: int, format_string: str) -> Any:
        """
        Reads a sequence of bytes from the given offset and converts it to format_string

        Args:
            offset (int): The position in the data source to start reading from.
            size (int): The number of bytes to read.
            format_string (str): The struct.unpack format string
        """
        ...

class Readable(IReadable):
    def __init__(self, obj: IReadable):
        self.obj = obj
    
    def seek(self, offset: int):
        self.obj.seek(offset)

    def tell(self) -> int:
        return self.obj.tell()

    def read(self, size: int):
        return self.obj.read(size)

    def read_at(self, offset: int, size: int):
        return self.obj.read_at(offset, size)

    def read_to(self, offset: int, size: int, format_string: str):
        return struct.unpack(format_string, self.read_at(offset, size))[0]

class File(Readable):
    obj: BufferedReader

    def __init__(self, file: str):
        super().__init__(open(file, "rb"))
    
    def fileno(self) -> int:
        return self.obj.fileno()

    def read_at(self, offset: int, size: int):
        self.seek(offset)
        return self.obj.read(size)


class OutOfBounds(Exception):
    ...

class MemoryRegion(IReadable):
    def __init__(self, source: bytearray):
        self.source = source
        self.pos = 0

    def tell(self):
        return self.pos

    def seek(self, pos):
        self.pos = pos

    def read(self, size):
        res = self.source[self.pos:size]
        self.pos += size
        return bytes(res)

    def read_at(self, offset, size):
        return bytes(self.source[offset:offset + size])
    
    def read_to(self, offset, size, format_str):
        return struct.unpack(format_str, self.read_at(offset, size))[0]

class Region(Readable):
    def __init__(self, source: IReadable, offset: int, end: int):
        """
        A region of a source
        
        Args:
            source (IReadable): An object that implements IReadable
            offset (int): The start of the region
            end (int): The end of the region
        """

        super().__init__(source)
        self.offset = offset
        self.end = end

    def calc_offset(self, offset: int):
        """
        Calculate the total offset by adding the provided offset to the instance's base offset.
        
        Args:
            offset (int): The offset value to add to the base offset
        
        Returns:
            int: The calculated offset
        
        Raises:
            OutOfBounds: If the offset is larger than self.end
        """

        total_offset = self.offset + offset
        if (total_offset > self.end):
            raise OutOfBounds(f"end: {self.end}, provided offset: {offset}, offset: {self.offset}")
        return total_offset

    def seek(self, offset):
        super().seek(self.calc_offset(offset))
    
    def read(self, size: int):
        current_pos = self.obj.tell() - self.offset
        remaining_bytes = self.end - current_pos

        if remaining_bytes <= 0:
            return None

        read_size = min(size, remaining_bytes)
        return super().read(read_size)
    
    def read_at(self, offset, size):
        return super().read_at(self.calc_offset(offset), size)

    def read_to(self, offset, size, format_string):
        return super().read_to(self.calc_offset(offset), size, format_string)