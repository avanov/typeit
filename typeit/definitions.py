from typing import Dict, NamedTuple, Union, Any

import colander as  col


OverridesT = Dict


class FieldDefinition(NamedTuple):
    source_name: str
    field_name: str
    field_type: Union[Any, NamedTuple]


class TypeExtension(NamedTuple):
    schema: col.SchemaNode
