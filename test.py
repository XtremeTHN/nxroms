from rominfo.rom import Nsp
from rominfo.nca.nca import ContentType, FsType
from colorama import Fore, Style
import sys

def color(string, color):
    return color + string + Fore.RESET

def colored(*msg, color=Fore.GREEN, level=""):
    print(color + Style.BRIGHT + str(level) + Style.RESET_ALL, *msg)

def color_ctx(prefix):
    def wrapper(*msg, color=Fore.GREEN, level=""):
        colored(*msg, color=color, level=str(prefix) + str(level))

    return wrapper         

def info(*msg):
    colored(*msg, level="INFO")

def print_nca_filesystems(nca):
    c = color_ctx("Header ")
    for index, header in enumerate(nca.fs_headers):
        c("filesystem:", header.fs_type, level=header.index)
        c("hash type:", header.hash_type, level=header.index)
        c("start_offset:", nca.fs_entries[index].start_offset, level=header.index)
        c("end_offset:", nca.fs_entries[index].end_offset, level=header.index)
        print()

def print_nca_info(nca):
    info("nca:", nca.name)
    info("rights id:", nca.rights_id)
    if hasattr(nca, "key_area"):
        info("key area:", nca.key_area)

    print()
    info("parsing filesystems in nca...")
    print_nca_filesystems(nca)

def print_all_ncas(rom):
    files = rom.get_files()

    print("-" * 50)
    for x in files:
        print_nca_info(x)
        print("-" * 50)

def control_nca(rom: Nsp):
    files = rom.get_files()

    for x in files:
        if x.content_type != ContentType.CONTROL:
            continue

        info("found control nca")
        print_nca_info(x)

        info("opening romfs")
        romfs = x.open_romfs(x.fs_headers[0])

        info("romfs header:", romfs.header)

        for f in romfs.files:
            c = color_ctx(f.name + ":")
            c(f"size {f.size} offset {f.offset}")

        print(romfs.get_file(romfs.files[1]).dump("control.nacp"))
        break
    else:
        info("control nca not found")

FILE = sys.argv[1]

info("parsing", color(FILE, Fore.CYAN))
p = Nsp(FILE)
p.populate_attrs()

control_nca(p)