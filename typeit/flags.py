from typing import Any, Tuple, Optional, Union, NamedTuple
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

# Disable strict matching of primitive types
# (for instance, allow '1' to be passed to a `x: int` attribute etc)
NON_STRICT_PRIMITIVES = _Flag('NON_STRICT_PRIMITIVES', True)


SUM_TYPE_DICT = _Flag('SUM_TYPE_DICT', 'type')


GLOBAL_NAME_OVERRIDE = _Flag('GLOBAL_NAME_OVERRIDE', lambda x: x)
