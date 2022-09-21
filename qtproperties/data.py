from dataclasses import dataclass


@dataclass
class Float2:
    x: float = 0
    y: float = 0


@dataclass
class Int2:
    x: int = 0
    y: int = 0

    def __post_init__(self):
        for attr in ('x', 'y'):
            setattr(self, attr, int(getattr(self, attr)))
