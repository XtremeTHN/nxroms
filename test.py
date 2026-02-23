from nxroms.nacp import Nacp
from nxroms.nca.header import ContentType
from nxroms.nca.nca import Nca
from nxroms.roms.nsp import Nsp
from nxroms.roms.xci import Xci
from nxroms.readers import File, MemoryRegion
from nxroms.utils import color_ctx, info
import sys


def print_nca_filesystems(nca: Nca):
    c = color_ctx("Header ")
    for index, header in enumerate(nca.header.fs_headers):
        c("filesystem:", header.fs_type, level=header.index)
        c("hash type:", header.hash_type, level=header.index)
        c(
            "start_offset:",
            nca.header.fs_entries[index].start_offset,
            level=header.index,
        )
        c("end_offset:", nca.header.fs_entries[index].end_offset, level=header.index)
        print()


def print_nca_info(nca: Nca):
    if hasattr(nca, "entry"):
        info("nca:", nca.entry.name)

    info("rights id:", nca.header.rights_id)
    if hasattr(nca, "key_area"):
        info("key area:", nca.header.key_area)

    print()
    info("parsing filesystems in nca...")
    print_nca_filesystems(nca)


def find_control_nca(nsp: Nsp):
    for x in nsp.get_ncas():
        if x.header.content_type != ContentType.CONTROL:
            continue

        print()
        info("found control nca")
        print_nca_info(x)

        fs = x.open_romfs(x.header.fs_headers[0])

        n = Nacp(fs.get_file(fs.files[0]))
        info("rom name:", n.titles[0].name)
        info("rom version:", n.version)

        return


def print_nsp(f):
    p = Nsp(f)

    info("all pfs0 entries:")
    for x in p.pfs.header.entry_table:
        info(x)

    find_control_nca(p)


def print_xci(f):
    p = Xci(f)

    info(p.header)
    info(p.hfs_header)

    s = p.open_partition("secure")

    info("all pfs0 entries:")
    for x in s.entry_table:
        info(x)


FILE = File(sys.argv[1])

print_xci(FILE)

FILE.close()
