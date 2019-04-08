from typing import Dict, NamedTuple, Union, Any, Mapping, Type

from .flags import _Flag

import colander as col


OverridesT = Mapping[
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


class FieldDefinition(NamedTuple):
    source_name: str
    field_name: str
    field_type: Union[Any, NamedTuple]


class TypeExtension(NamedTuple):
    schema: col.SchemaNode
