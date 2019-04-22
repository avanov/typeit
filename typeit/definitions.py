from typing import NamedTuple, Union, Any, Type

from pyrsistent import pmap
from pyrsistent.typing import PMap

from .flags import _Flag


OverridesT = PMap[
    Union[
        # field name override
        property,
        # flag override
        _Flag,
        # new type extension
        Type
    ],
    Any
]


NO_OVERRIDES: OverridesT = pmap()


class FieldDefinition(NamedTuple):
    source_name: str
    field_name: str
    field_type: Union[Any, NamedTuple]
