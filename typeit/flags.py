from typing import Tuple, Any


class _Flag:
    def __lshift__(self, other: Any) -> Tuple['_Flag', Any]:
        return (self, other)

# Disable strict matching of primitive types
# (for instance, allow '1' to be passed to a `x: int` attribute etc)
NON_STRICT_PRIMITIVES = _Flag()


SUM_TYPES_AS_DICT = _Flag()
