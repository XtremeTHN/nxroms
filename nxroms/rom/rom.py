from ..readers import IReadable, Readable, File


class Rom(Readable):
    def __init__(self, obj: IReadable | str):
        if isinstance(obj, str):
            o = File(obj)
            super().__init__(o)
        elif isinstance(obj, IReadable):
            super().__init__(obj)
        else:
            raise ValueError("expected a file path or an object implementing IReadable")
