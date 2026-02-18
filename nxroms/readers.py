import struct
from typing import Any
from io import BufferedReader
from abc import ABC, abstractmethod
from .keys import Keyring, modes
from pathlib import Path


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
    def skip(self, bytes: int) -> Any:
        """
        Skips a count of `bytes` from the current position

        Args:
            bytes (int): Count of bytes to skip
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
    def read_unpack(self, size: int, format_string: str) -> Any:
        """
        Reads up to `size` bytes from the source and unpacks it to `format_string`

        Args:
            size (int): The maximum number of bytes to read.
            format_string (str): The struct.unpack format string

        Returns:
            Any | None: The unpacked data. None if theres no more data to read.
        """
        ...

    # TODO: change name to read_unpack_at
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

    @abstractmethod
    def dump(self, path):
        """
        Writes all the data of this `IReadable` into `path`

        Args:
            path (str): The destination path
        """
        ...


class Readable(IReadable):
    def __init__(self, obj: IReadable):
        """
        A wrapper of an `IReadable`

        Args:
            obj (IReadable): An object implementing the mayority of methods of IReadable
        """
        self.obj = obj

    def seek(self, offset: int):
        self.obj.seek(offset)

    def skip(self, bytes: int):
        self.seek(self.obj.tell() + bytes)

    def tell(self) -> int:
        return self.obj.tell()

    def read(self, size: int):
        return self.obj.read(size)

    def read_unpack(self, size: int, format_str: int):
        d = self.read(size)
        if not d:
            return

        return struct.unpack(format_str, d)[0]

    # TODO: change this to read_unpack
    def _read_to(self, size: int, format_str: str):
        r = self.read(size)
        return struct.unpack(format_str, r)[0]

    def read_at(self, offset: int, size: int):
        return self.obj.read_at(offset, size)

    # TODO: change name to read_unpack_at
    def read_to(self, offset: int, size: int, format_string: str):
        return struct.unpack(format_string, self.read_at(offset, size))[0]

    def dump(self, path):
        self.seek(0)
        with open(path, "wb") as f:
            while True:
                chunk = self.read(1024)
                if not chunk:
                    break
                f.write(chunk)


class File(Readable):
    obj: BufferedReader

    def __init__(self, file: str | BufferedReader | Path):
        if isinstance(file, str):
            super().__init__(open(file, "rb"))
        elif isinstance(file, Path):
            super().__init__(file.open("rb"))
        elif isinstance(file, BufferedReader):
            super().__init__(file)
        else:
            raise ValueError(f"invalid object: {type(file)}")

    def fileno(self) -> int:
        return self.obj.fileno()

    def read_at(self, offset: int, size: int):
        self.seek(offset)
        return self.obj.read(size)

    def close(self):
        self.obj.close()


class OutOfBounds(Exception): ...


class MemoryRegion(IReadable):
    def __init__(self, source: bytearray):
        """
        A readable bytes buffer
        """
        self.source = source
        self.pos = 0

    def tell(self):
        return self.pos

    def seek(self, pos):
        self.pos = pos

    def skip(self, bytes: int):
        self.seek(self.obj.tell() + bytes)

    def read(self, size):
        res = self.source[self.pos : self.pos + size]
        self.pos += size

        return bytes(res)

    # TODO: implement
    def read_unpack(self, size, format_string):
        return self._read_to(size, format_string)

    # TODO: remove
    def _read_to(self, size: int, format_str: str):
        r = self.read(size)
        return struct.unpack(format_str, r)[0]

    def read_at(self, offset, size):
        return self.source[offset : offset + size]

    # TODO: change name to read_unpack_at
    def read_to(self, offset, size, format_str):
        return struct.unpack(format_str, self.read_at(offset, size))[0]

    def __len__(self):
        return len(self.source)

    def dump(self, path):
        self.seek(0)
        with open(path, "wb") as f:
            f.write(self.source)


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
        if total_offset > self.end:
            return total_offset
            raise OutOfBounds(
                f"total_offset: {total_offset} end: {self.end} self.offset: {self.offset}"
            )
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


class EncryptedCtrRegion(Readable):
    def __init__(self, source: Region, offset: int, end: int, key: bytes, ctr: int):
        """
        A region with a ctr encryption

        Args:
            source (Region): The source
            offset (int): The start of the encryted data
            end (int): The end of the encrypted data
            key (bytes): The AES Ctr key in bytes
            ctr (int): The ctr of the header
        """
        super().__init__(source)

        self.start = offset
        self.offset = offset
        self.end = end

        self.key = key
        self.ctr = ctr

    def align_down(self, value: int, align: int):
        return value & ~(align - 1)

    def align_up(self, value: int, align: int):
        return (value + (align - 1)) & ~(align - 1)

    # im not gonna refactor this
    def read(self, size):
        if self.offset >= self.end:
            return b""

        remaining = self.end - self.offset
        size = min(size, remaining)

        aligned_offset = self.align_down(self.offset, 0x10)
        diff = self.offset - aligned_offset

        size_raw = size + diff
        buf_size = self.align_up(size_raw, 0x10)

        self.obj.seek(aligned_offset)
        data = self.obj.read(buf_size)

        if not data:
            return b""

        sector_index = (aligned_offset >> 4) | (self.ctr << 64)
        iv = Keyring.get_tweak(sector_index)

        decryptor = Keyring.get_decryptor(self.key, modes.CTR(iv))
        decrypted = decryptor.update(data)

        start = diff
        end = min(start + size, len(decrypted))

        result = decrypted[start:end]

        self.offset += len(result)

        return result

    def calc_offset(self, offset):
        _offset = self.start + offset
        if _offset > self.end:
            raise OutOfBounds()
        return _offset

    def seek(self, offset):
        self.offset = self.calc_offset(offset)

    def read_at(self, offset, size):
        self.seek(offset)
        return self.read(size)

    def read_to(self, offset, size, format_string):
        self.seek(offset)
        d = self.read(size)
        return struct.unpack(format_string, d)[0]
