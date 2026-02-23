from ..fs.pfs0 import PFSHeader, PFS0
from ..readers import IReadable
from ..nca.nca import Nca
import os


class Nsp(PFS0):
    def __init__(self, source: IReadable, header: PFSHeader = None):
        super().__init__(source, header)

    def get_nca(self, index: int):
        item = self.get_item(index)
        if os.path.splitext(item.entry.name)[1] != ".nca":
            return None

        return Nca.from_item(item)

    def get_ncas(self) -> list[Nca]:
        return [
            Nca.from_item(x)
            for x in self.get_items()
            if os.path.splitext(x.entry.name)[1] == ".nca"
        ]
