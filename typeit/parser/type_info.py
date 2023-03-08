from typing import Type, get_type_hints, NamedTuple, Union, ForwardRef, Any, Generator

NoneType = type(None)


class AttrInfo(NamedTuple):
    name: str
    resolved_type: Type
    raw_type: Union[Type, ForwardRef]


def get_type_attribute_info(typ: Type) -> Generator[AttrInfo, Any, None]:
    raw = getattr(typ, '__annotations__', {})
    existing_only = lambda x: x[1] is not NoneType
    return (AttrInfo(name, t, raw.get(name, t)) for name, t in filter(existing_only, get_type_hints(typ).items()))
