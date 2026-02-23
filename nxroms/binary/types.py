from enum import Enum as e
from typing import Any

from nxroms.utils import is_all_zero
from ..readers import IReadable


class DataTypeDescriptor:
    def __init__(self, size, offset, format_str=None):
        self.__size = size
        self.__offset = offset
        self.__format_str = format_str
        self.__value = None

        self.name = None

    @property
    def offset(self) -> int:
        return self.__offset

    @property
    def value(self) -> Any:
        return self.__value

    @property
    def format_string(self) -> str:
        return self.__format_str

    @property
    def size(self) -> int:
        return self.__size

    def convert(self, val) -> Any | None:
        return val

    def get_value(self, obj: IReadable):
        if self.__format_str:
            val = self.convert(
                obj.peek_unpack_at(self.__offset, self.__size, self.__format_str)
            )
        else:
            val = self.convert(obj.peek_at(self.__offset, self.__size))

        return val

    def __set_name__(self, owner, name):
        self.name = "_" + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        if self.name not in obj.__dict__:
            setattr(obj, self.name, self.get_value(obj))
        return getattr(obj, self.name, None)


class DataType(DataTypeDescriptor):
    value: Any
    size: int
    format_string: str

    def __init__(self, offset, _class=None):
        self._class = _class
        super().__init__(self.size, offset, self.format_string)

    def convert(self, value):
        if self._class is not None:
            return self._class(value)
        return value


class UInt32(DataType):
    format_string = "<I"
    value: int
    size = 0x4


class UInt64(DataType):
    format_string = "<Q"
    value: int
    size = 0x8


class Bytes(DataTypeDescriptor):
    value: bytes

    def __init__(self, offset: int, size: int, _class=None):
        """
        A bytes descriptor. If the buffer is all zero, it will return None
        """

        self._class = _class
        super().__init__(size, offset)

    def convert(self, value):
        if self._class is not None:
            return self._class(value)
        return None if is_all_zero(value) else value


class Enumeration(DataTypeDescriptor):
    def __init__(self, offset: int, enum_class: e):
        super().__init__(1, offset)
        self.enum_class = enum_class

    def convert(self, value):
        return self.enum_class(value[0])
