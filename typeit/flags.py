from typing import Any, Optional, Union, NamedTuple
from .combinator.combinator import Combinator


class _ModifiedFlag(NamedTuple):
    flag: '_Flag'
    new_value: Any


class _Flag:
    def __init__(self, name: str, default_setting: Any):
        """ Default settings should not be modified once they are
        set by object instantiation. If you need to override them,
        use the __call__ method.
        """
        self.name = name
        self.default_setting = default_setting

    def __repr__(self) -> str:
        return f'Flag({self.name})'

    def __call__(self, other: Optional[Any] = None) -> Union['_Flag', _ModifiedFlag]:
        """ returned tuple will be handled by a type constructor,
        see `isinstance(override, _ModifiedFlag)`
        """
        if other:
            return _ModifiedFlag(self, other)
        return self

    def __and__(self, other: Any) -> Combinator:
        return Combinator() & self & other


Identity = lambda x: x

# Disable strict matching of primitive types
# (for instance, allow '1' to be passed to a `x: int` attribute etc)
NonStrictPrimitives = _Flag('NonStrictPrimitives', True)


SumTypeDict = _Flag('SumTypeDict', 'type')


GlobalNameOverride = _Flag('GlobalNameOverride', Identity)


# fo b/w compatibility
NON_STRICT_PRIMITIVES = NonStrictPrimitives
SUM_TYPE_DICT = SumTypeDict