from typing import Optional, Dict, NamedTuple, Union, Any

import colander as  col


OverridesT = Optional[Dict]


class FieldDefinition(NamedTuple):
    source_name: str
    field_name: str
    field_type: Union[Any, NamedTuple]


class TypeExtension(NamedTuple):
    schema: col.SchemaNode
