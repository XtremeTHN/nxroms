from dataclasses import dataclass

from nxroms.fs.fs import EncryptionType, FsHeader, FsType, HashType, InvalidFs
from nxroms.fs.pfs0 import PFS0, PFSEntry, PFSItem, Readable
from nxroms.fs.romfs import RomFS
from nxroms.keyring import Keyring
from nxroms.nca.header import NcaHeader
from nxroms.readers import CTRReadable, IReadable, ReadableRegion


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

    def get_entry_for_header(self, header: FsHeader):
        return [x for x in self.header.fs_entries if x.index == header.index][0]

    def open_fs(self, header: FsHeader):
        def get_enc_region(offset, end_offset):
            key = bytes.fromhex(self.header.key_area.aes_ctr_key)
            return CTRReadable(self, offset, end_offset, key, header.ctr)

        entry = self.get_entry_for_header(header)

        if header.encryption_type != EncryptionType.AES_CTR:
            raise Exception(
                "Only aes ctr encryption is supported", header.encryption_type
            )

        fs_offset = 0
        match header.hash_type:
            case HashType.HIERARCHICAL_INTEGRITY_HASH:
                fs_offset = (
                    entry.start_offset
                    + header.hash_data.info_level_hash.levels[-1].logical_offset
                )
            case HashType.HIERARCHICAL_SHA256_HASH:
                fs_offset = (
                    entry.start_offset + header.hash_data.layer_regions[1].offset
                )
            case _:
                raise Exception("invalid hash type")

        return get_enc_region(fs_offset, entry.end_offset)

    def open_pfs(self, header: FsHeader):
        if header.fs_type != FsType.PARTITION_FS:
            raise InvalidFs(FsType.PARTITION_FS, header.fs_type)

        fs = self.open_fs(header)
        return PFS0(fs)

    def open_romfs(self, header: FsHeader):
        if header.fs_type != FsType.ROM_FS:
            raise InvalidFs(FsType.ROM_FS, header.fs_type)

        return RomFS(self.open_fs(header))
