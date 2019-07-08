from typing import Any, Tuple, Optional
from .combinator.combinator import Combinator


class _Flag:
    def __init__(self, default_setting):
        """ Default settings should not be modified once they are
        set by object instantiation. If you need to override them,
        use the __call__ method.
        """
        self.default_setting = default_setting

    def __call__(self, other: Optional[Any] = None) -> Tuple['_Flag', Any]:
        return (self, other)

    def __and__(self, other: Any) -> Combinator:
        return Combinator() & self & other

# Disable strict matching of primitive types
# (for instance, allow '1' to be passed to a `x: int` attribute etc)
NON_STRICT_PRIMITIVES = _Flag(True)


SUM_TYPE_DICT = _Flag('type')
