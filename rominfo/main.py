from rom import Nsp
from nca import ContentType
from colorama import Fore, Style

p = Nsp("undertale.nsp")
p.populate_attrs()

print(
    "partition_entry_count:", p.partition_entry_count,
    "string_table_size:", p.string_table_size,
    "reserved:", p.reserved
)

file = p.get_files()

for x in file:
    if x.content_type == ContentType.CONTROL:
        print(Style.BRIGHT + Fore.GREEN + "FOUND" + Style.RESET_ALL)
        print(x.name, x.sdk_addon_version)

# for x in p.get_files():
#     print(x.name, x.entry.size)
#     n = open(f"out/{x.name}", "wb")
    
#     while True:
#         chunk = x.read(1024)
#         if not chunk:
#             print("end", x.entry.offset, x.entry.size, x.tell())
#             break

#         n.write(chunk)
#         del chunk
