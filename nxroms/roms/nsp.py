from ..fs.nca_fs import NcaFS
from ..fs.pfs0 import PFSHeader
from ..readers import IReadable


class Nsp(NcaFS):
    def __init__(self, source: IReadable):
        pfs = PFSHeader(self, b"PFS0", 0x18)
        super().__init__(source, pfs)
