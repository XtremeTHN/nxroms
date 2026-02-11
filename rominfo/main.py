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

file = p.get_file(2)

print(file.content_type, file.content_size)

for x in file.fs_entries:
    print(x, x.start_offset, x.end_offset)

for x in file.fs_headers:
    print(x)
# print(file.fs_entries[1].start_offset, file.fs_entries[1].end_offset)
# file.decrypted_header.dump(f"{file.name}.bin")

# file.get_fs_header_for_section(0
# file.populate_fs_entries()

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
