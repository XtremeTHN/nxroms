from dataclasses import dataclass

from nxroms.fs.pfs0 import PFSEntry, PFSItem, Readable
from nxroms.keyring import Keyring
from nxroms.nca.header import NcaHeader
from nxroms.readers import IReadable


@dataclass
class Nca(Readable):
    header: NcaHeader
    entry: PFSEntry | None = None

    def __init__(self, source: IReadable):
        super().__init__(source)

        self.keyring = Keyring.get_default()
        header = source.peek_at(0, 0xC00)
        self.header = NcaHeader(header)

    @classmethod
    def from_item(self, item: PFSItem):
        self.entry = item.entry
        return Nca(item)
