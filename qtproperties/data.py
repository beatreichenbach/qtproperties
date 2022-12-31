from dataclasses import dataclass
import math

# TODO: implement operations
# TODO: it is possible to assign string for x and y, why?

@dataclass
class Int2:
    x: int = 0
    y: int = 0

    def __post_init__(self):
        for attr in ('x', 'y'):
            value = getattr(self, attr)
            if isinstance(value, float):
                value = math.floor(value)
            setattr(self, attr, int(value))

    def __iter__(self):
        return iter((self.x, self.y))

    def __truediv__(self, other):
        x = self.x.__truediv__(other.x)
        y = self.y.__truediv__(other.y)
        return self.__class__(x, y)

    def __floordiv__(self, other):
        x = self.x.__floordiv__(other.x)
        y = self.y.__floordiv__(other.y)
        return self.__class__(x, y)

    def __add__(self, other):
        x = self.x + other.x if isinstance(other, self.__class__) else self.x + other
        y = self.y + other.y if isinstance(other, self.__class__) else self.y + other
        return self.__class__(x, y)

    def __sub__(self, other):
        x = self.x - other.x if isinstance(other, self.__class__) else self.x - other
        y = self.y - other.y if isinstance(other, self.__class__) else self.y - other
        return self.__class__(x, y)

    def __mul__(self, other):
        x = self.x * other.x if isinstance(other, self.__class__) else self.x * other
        y = self.y * other.y if isinstance(other, self.__class__) else self.y * other
        return self.__class__(x, y)

# TODO: inherit from Int2
@dataclass
class Float2:
    x: float = 0
    y: float = 0

    def __iter__(self):
        return iter((self.x, self.y))

    def __truediv__(self, other):
        x = self.x.__truediv__(other.x)
        y = self.y.__truediv__(other.y)
        return self.__class__(x, y)

    def __floordiv__(self, other):
        x = self.x.__floordiv__(other.x)
        y = self.y.__floordiv__(other.y)
        return self.__class__(x, y)

    def __add__(self, other):
        x = self.x + other.x if isinstance(other, self.__class__) else self.x + other
        y = self.y + other.y if isinstance(other, self.__class__) else self.y + other
        return self.__class__(x, y)

    def __sub__(self, other):
        x = self.x - other.x if isinstance(other, self.__class__) else self.x - other
        y = self.y - other.y if isinstance(other, self.__class__) else self.y - other
        return self.__class__(x, y)

    def __mul__(self, other):
        x = self.x * other.x if isinstance(other, self.__class__) else self.x * other
        y = self.y * other.y if isinstance(other, self.__class__) else self.y * other
        return self.__class__(x, y)
