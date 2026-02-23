import os

from ..readers import IReadable, Readable
from ..fs.pfs0 import PFS0, PFSHeader
from ..nca.nca import Nca


class NcaFS(Readable):
    def __init__(self, source: IReadable, header: PFSHeader):
        super().__init__(source)
        self.header = header

    def get_nca(self, index: int):
        item = self.pfs.get_item(index)
        if os.path.splitext(item.entry.name)[1] != ".nca":
            return None

        return Nca.from_item(item)

    def get_ncas(self) -> list[Nca]:
        return [
            Nca.from_item(x)
            for x in self.pfs.get_items()
            if os.path.splitext(x.entry.name)[1] == ".nca"
        ]
