# rominfo
Python project to parse nsp and xci files.

I took some code from [cntx](https://github.com/XorTroll/cntx) and [hactool](https://github.com/XorTroll/cntx)

```
from rominfo.rom import Nsp

n = Nsp("rom.nsp")

ncas = n.get_files()

for x in ncas:
    x.dump(x.name)
``` 