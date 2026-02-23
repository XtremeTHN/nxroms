# rominfo
Python project to parse nsp and xci files.

```python
from nxroms.roms import Nsp

n = Nsp("rom.nsp")

ncas = n.get_ncas()

for x in ncas:
    x.dump(x.name)
``` 
