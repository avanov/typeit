from typing import NamedTuple, Union, Any, Mapping, Type

from pyrsistent import pmap
from pyrsistent.typing import PMap

from .flags import _Flag

import colander as col


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


OverrideT = Union[
    # flag override
    _Flag,
    # new type extension
    Type,
    Mapping[property, str],
]


NO_OVERRIDES: OverridesT = pmap()


class FieldDefinition(NamedTuple):
    source_name: str
    field_name: str
    field_type: Union[Any, NamedTuple]


class TypeExtension(NamedTuple):
    schema: col.SchemaNode
