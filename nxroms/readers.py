from io import BufferedReader, BytesIO
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
import struct


class IReadable(ABC):
    @abstractmethod
    def read(self, size) -> bytes | None:
        """
        Reads from current cursor position to size

        Args:
            size (int): The count of bytes to read

        Returns:
            The data or None
        """
        ...

    @abstractmethod
    def read_unpack(self, size, format_str) -> Any | None:
        """
        Reads from current cursor position to size, and then converts to format_str

        Args:
            size (int): The count of bytes to read
            format_str (str): The struct.unpack format string

        Returns:
            The unpacked data or None
        """
        ...

    @abstractmethod
    def read_at(self, offset, size) -> bytes | None:
        """
        Reads at `offset` to `size`. This method moves the cursor

        Args:
            offset (int): The offset
            size (int): The count of bytes to read
        Returns:
            The data in bytes or None
        """
        ...

    @abstractmethod
    def read_unpack_at(self, offset, size, format_str) -> Any | None:
        """
        Reads at `offset` to `size` and then converts it to `format_str`. This method moves the cursor

        Args:
            offset (int): The offset
            size (int): The count of bytes to read
            format_str (str): The struct.unpack format string
        Returns:
            The unpacked data or None
        """
        ...

    @abstractmethod
    def peek(self, size) -> bytes | None:
        """
        Reads from current cursor position to `size`. This method does not move the cursor

        Args:
            size (int): The count of bytes to read
        Returns:
            The data in bytes or None
        """
        ...

    @abstractmethod
    def peek_unpack(self, size, format_str) -> Any | None:
        """
        Reads from current cursor position to size, and then converts to format_str. This method does not move the cursor

        Args:
            size (int): The count of bytes to read
            format_str (str): The struct.unpack format string

        Returns:
            The unpacked data or None
        """
        ...

    @abstractmethod
    def peek_at(self, offset, size) -> bytes | None:
        """
        Reads at `offset` to `size`. This method does not move the cursor

        Args:
            offset (int): The offset
            size (int): The count of bytes to read
        Returns:
            The data in bytes or None
        """
        ...

    @abstractmethod
    def peek_unpack_at(self, offset, size, format_str) -> Any | None:
        """
        Reads at `offset` to `size` and then converts it to `format_str`. This method does not move the cursor

        Args:
            offset (int): The offset
            size (int): The count of bytes to read
            format_str (str): The struct.unpack format string
        Returns:
            The unpacked data or None
        """
        ...

    @abstractmethod
    def tell(self) -> int:
        """
        Gets the cursor position

        Returns:
            The current cursor position
        """
        ...

    @abstractmethod
    def seek(self, offset):
        """
        Moves the cursor to offset

        Args:
            offset (int): The offset
        """
        ...

    @abstractmethod
    def skip(self):
        """
        Skips `count` of bytes

        Args:
            count (int): The count of bytes
        """
        ...


class Readable(IReadable):
    def __init__(self, source: IReadable):
        self.source = source

    def __unpack(self, data: bytes, format_str: str):
        return struct.unpack(format_str, data)[0]

    def __read_unpack(self, method, size, format_str):
        data = method(size)
        if not data:
            return
        if len(data) < size:
            raise EOFError(f"expected {size} bytes, got {len(data)}")

        return self.__unpack(data, format_str)

    def __read_at(self, method, offset, size):
        self.seek(offset)
        return method(size)

    def __read_unpack_at(self, method, offset, size, format_str):
        data = method(offset, size)
        if not data:
            return

        return self.__unpack(data, format_str)

    def read(self, size) -> bytes | None:
        return self.source.read(size)

    def read_unpack(self, size, format_str) -> Any | None:
        return self.__read_unpack(self.read, size, format_str)

    def read_at(self, offset, size) -> bytes | None:
        return self.__read_at(self.read, offset, size)

    def read_unpack_at(self, offset, size, format_str) -> Any | None:
        return self.__read_unpack_at(self.read_at, offset, size, format_str)

    def peek(self, size) -> bytes | None:
        orig = self.tell()
        data = self.read(size)
        self.seek(orig)
        return data

    def peek_unpack(self, size, format_str) -> Any | None:
        return self.__read_unpack(self.peek, size, format_str)

    def peek_at(self, offset, size) -> bytes | None:
        return self.__read_at(self.peek, offset, size)

    def peek_unpack_at(self, offset, size, format_str) -> Any | None:
        return self.__read_unpack_at(self.peek_at, offset, size, format_str)

    def tell(self) -> int:
        return self.source.tell()

    def seek(self, offset):
        self.source.seek(offset)

    def skip(self, count: int):
        self.seek(self.tell() + count)

    def dump(self, name: str = "out.bin"):
        with open(name, "wb") as f:
            while True:
                chunk = self.read(1024)
                if not chunk:
                    break
                f.write(chunk)


class ReadableRegion(IReadable):
    def __init__(self, source: IReadable, start: int, size: int):
        self._source = source
        self._start = start
        self._size = size
        self._pos = 0  # local cursor

    def _absolute(self, offset: int) -> int:
        return self._start + offset

    def read(self, size):
        if self._pos >= self._size:
            return None

        size = min(size, self._size - self._pos)

        data = self._source.peek_at(self._absolute(self._pos), size)
        self._pos += len(data)
        return data

    def read_at(self, offset, size):
        if offset >= self._size:
            return None

        size = min(size, self._size - offset)
        self._pos = offset
        return self._source.peek_at(self._absolute(offset), size)

    def peek(self, size):
        if self._pos >= self._size:
            return None

        size = min(size, self._size - self._pos)
        return self._source.peek_at(self._absolute(self._pos), size)

    def peek_at(self, offset, size):
        if offset >= self._size:
            return None

        size = min(size, self._size - offset)
        return self._source.peek_at(self._absolute(offset), size)

    def tell(self):
        return self._pos

    def seek(self, offset):
        if not (0 <= offset <= self._size):
            raise ValueError("Offset out of bounds")
        self._pos = offset

    def skip(self, count):
        self.seek(self._pos + count)

    # Optional: reuse your Readable helpers for unpack
    def read_unpack(self, size, format_str):
        data = self.read(size)
        if not data or len(data) < size:
            return None
        return struct.unpack(format_str, data)[0]

    def peek_unpack(self, size, format_str):
        data = self.peek(size)
        if not data or len(data) < size:
            return None
        return struct.unpack(format_str, data)[0]

    def read_unpack_at(self, offset, size, format_str):
        data = self.read_at(offset, size)
        if not data or len(data) < size:
            return None
        return struct.unpack(format_str, data)[0]

    def peek_unpack_at(self, offset, size, format_str):
        data = self.peek_at(offset, size)
        if not data or len(data) < size:
            return None
        return struct.unpack(format_str, data)[0]

    def dump(self, name: str = "out.bin"):
        with open(name, "wb") as f:
            while True:
                chunk = self.read(1024)
                if not chunk:
                    break
                f.write(chunk)


class File(Readable):
    source: BufferedReader

    def __init__(self, obj: BufferedReader | Path | str):
        if isinstance(obj, BufferedReader):
            super().__init__(obj)
        elif isinstance(obj, Path):
            super().__init__(obj.open("rb"))
        elif isinstance(obj, str):
            super().__init__(open(obj, "rb"))
        else:
            raise ValueError(
                f"Invalid object type: expected a BufferedReader, Path, or a string, got {type(obj)}"
            )

    def close(self):
        self.source.close()

    def fileno(self):
        return self.source.fileno()


class MemoryRegion(Readable):
    def __init__(self, source: bytes):
        super().__init__(BytesIO(source))
