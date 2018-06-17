import re
from typing import Type, Tuple, Optional, Any, Union, List, Dict, NamedTuple, Callable

import inflection


JsonType = Union[
    bool,
    int,
    float,
    str,
    List[Any],
    Dict[str, Any],
    None
]


JSON_TO_BUILTIN_TYPES = {
    True.__class__: bool,
    (0).__class__: int,
    (0.0).__class__: float,
    ''.__class__: str,
    [].__class__: List[Any],
    {}.__class__: Dict[str, Any],
    None.__class__: Optional[Any],
}


_type_name_getter = lambda typ: typ.__name__


BUILTIN_LITERALS_FOR_TYPES = {
    # Note that we don't have a record for Dict here,
    # because it is clarified to a concrete NamedTuple
    # earlier in the parsing process.
    bool: _type_name_getter,
    int: _type_name_getter,
    float: _type_name_getter,
    str: _type_name_getter,
    List[Any]: _type_name_getter,
    # We need explicit [Any] to avoid errors like:
    #   TypeError: Plain typing.Optional is not valid as type argument
    Optional[Any]: lambda __: 'Optional[Any]',
}


def literal_for_type(typ) -> str:
    # typ is either one of these:
    #   * builtin type
    #   * concrete NamedTuple
    #   * clarified List (i.e. non List[Any])
    try:
        return BUILTIN_LITERALS_FOR_TYPES[typ](typ)
    except KeyError:
        if typ.__class__ is List.__class__:
            sub_type = literal_for_type(typ.__args__[0])
            return f'List[{sub_type}]'
        # typ: NamedTuple
        return typ.__name__


class Component(NamedTuple):
    field_name: str
    field_type: Union[Any, NamedTuple]


def type_for(obj: JsonType) -> Type[JsonType]:
    return JSON_TO_BUILTIN_TYPES[obj.__class__]


def parse(struct: Dict[str, JsonType],
          components: List[Component],
          parent_prefix: str = '') -> List[Component]:
    for field_name, field_struct in struct.items():
        field_name, was_normalized = normalize_name(field_name)
        field_type = clarify_struct_type(field_name, field_struct, parent_prefix)
        components.append(Component(field_name, field_type))
    return components


def clarify_struct_type(field_name, field_struct, parent_prefix):
    field_type = type_for(field_struct)
    clarifier: Callable = FIELD_TYPE_CLARIFIERS[field_type]
    field_type = clarifier(field_name, field_struct, parent_prefix)
    return field_type


def clarify_field_type_dict(field_name: str,
                            field_struct: JsonType,
                            parent_prefix: str) -> NamedTuple:
    if parent_prefix:
        type_name = f'{parent_prefix}_{field_name}'
    else:
        type_name = field_name
    sub_struct = parse(field_struct, [], type_name)
    field_type = construct_type(type_name, sub_struct)
    return field_type


def clarify_field_type_list(field_name, field_struct: List[Any], parent_prefix):
    if len(field_struct):
        inner_struct = field_struct[0]
        field_type = clarify_struct_type(field_name, inner_struct, parent_prefix)
    else:
        field_type = Any
    return List[field_type]


FIELD_TYPE_CLARIFIERS = {
    Dict[str, Any]: clarify_field_type_dict,
    List[Any]: clarify_field_type_list,
    str: lambda a, b, c: str,
    int: lambda a, b, c: int,
    bool: lambda a, b, c: bool,
    Optional[Any]: lambda a, b, c: Optional[Any],
}

def normalize_name(name: str,
                   pattern=re.compile('^([_0-9]+).*$')) -> Tuple[str, bool]:
    """ Some field name patterns are not allowed in namedtuples
    https://docs.python.org/3.7/library/collections.html#collections.namedtuple
    """
    if pattern.match(name):
        return f'normalized__{name}', True
    return name, False


def construct_type(name: str, fields: List[Component]) -> NamedTuple:
    type_fields: List[Tuple[str, NamedTuple]] = []
    for c in fields:
        if c.field_type is Dict[str, Any]:
            sub_type_name = inflection.camelize(f'{name}_{c.field_name}')
            field_type = construct_type(sub_type_name, c.field_type)
        else:
            field_type = c.field_type
        type_fields.append((c.field_name, field_type))

    return NamedTuple(inflection.camelize(name), type_fields)


def codegen(constructed: NamedTuple,
            top: bool = True,
            indent: int = 4) -> str:
    ind = ' ' * indent
    code = [f'class {constructed.__name__}(NamedTuple):']
    if not constructed._field_types:
        code.append(f'{ind}...\n\n')

    for field_name, field_type in constructed._field_types.items():
        type_literal = literal_for_type(field_type)
        if field_type not in BUILTIN_LITERALS_FOR_TYPES:
            # field_type: Union[NamedTuple, List]
            folded_lists_count = type_literal.count('List[')
            if folded_lists_count:
                # field_type: List[T]
                # traverse to the folded object
                for __ in range(folded_lists_count):
                    field_type = field_type.__args__[0]

                if field_type not in BUILTIN_LITERALS_FOR_TYPES:
                    sub = codegen(field_type, False)
                    code.insert(0, f'{sub}\n\n')
            else:
                # field_type: NamedTuple
                # Generate a folded structure definition in the global scope
                # and then use it for the current field
                sub = codegen(field_type, False)
                code.insert(0, f'{sub}\n\n')

        code.append(f'{ind}{field_name}: {type_literal}')

    if top:
        code = ['from typing import NamedTuple, Dict, Any, List, Optional\n\n'] + code
    return '\n'.join(code)
