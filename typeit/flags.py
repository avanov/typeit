from typing import Any, Tuple
from .combinator.combinator import Combinator


class _Flag:
    def __init__(self, default_setting):
        self.default_setting = default_setting

    def __lshift__(self, other: Any) -> Tuple['_Flag', Any]:
        return (self, other)

    def __and__(self, other: Any) -> Combinator:
        return Combinator() & self & other

# Disable strict matching of primitive types
# (for instance, allow '1' to be passed to a `x: int` attribute etc)
NON_STRICT_PRIMITIVES = _Flag(True)


SUM_TYPE_DICT = _Flag('type')
