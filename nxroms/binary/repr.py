from .types import DataTypeDescriptor

class BinaryRepr:
    def __repr__(self):
        cls = self.__class__.__name__
        fields = []

        for name, attr in self.__class__.__dict__.items():
            if isinstance(attr, (DataTypeDescriptor)):
                value = getattr(self, name)
                fields.append(f"{name}={value!r}")
            
        for name, value in self.__dict__.items():
            if name.startswith("_"):
                continue
            fields.append(f"{name}={value!r}")

        return f"{cls}({', '.join(fields)})"