from ..fs.pfs0 import PFS0
from ..readers import File, IReadable
from ..nca.nca import Nca
from pathlib import Path
import os


class Nsp(PFS0):
    def __init__(self, rom: IReadable | File | Path | str):
        if isinstance(rom, str) or isinstance(rom, Path):
            rom = File(rom)
        super().__init__(rom)

    def get_file(self, index: int) -> Nca | None:
        if os.path.splitext(self.header.file_entry_table[index].name)[1] != ".nca":
            return None

        return Nca.from_entry(
            self, self.header.file_entry_table[index], self.header.raw_data_pos
        )

    def get_files(self) -> list[Nca]:
        ncas = []

        for x in range(self.header.file_count):
            n = self.get_file(x)
            if not n:
                continue
            ncas.append(n)

        return ncas
