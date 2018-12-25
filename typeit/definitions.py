from typing import Optional, Dict, NamedTuple, Union, Any


OverridesT = Optional[Dict]


class FieldDefinition(NamedTuple):
    source_name: str
    field_name: str
    field_type: Union[Any, NamedTuple]
