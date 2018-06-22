import re
from typing import (
    Type, Tuple, Optional, Any, Union, List,
    Dict, NamedTuple, Callable
)

import inflection
import colander as col
import typing_inspect as insp


BuiltinTypes = Union[
    bool,
    int,
    float,
    str,
]

JsonType = Union[
    BuiltinTypes,
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


def literal_for_type(typ: Type) -> str:
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
          parent_prefix: str = '') -> List[Component]:
    """ Parser's entry point
    """
    components: List[Component] = []
    for field_name, field_struct in struct.items():
        field_name, was_normalized = normalize_name(field_name)
        field_type = clarify_struct_type(field_name, field_struct, parent_prefix)
        components.append(Component(field_name, field_type))
    return components


def clarify_struct_type(field_name: str,
                        field_struct: Any,
                        parent_prefix: str) -> Type:
    field_type = type_for(field_struct)
    clarifier: Callable[[str, Any, str], Type] = FIELD_TYPE_CLARIFIERS[field_type]
    field_type = clarifier(field_name, field_struct, parent_prefix)
    return field_type


def clarify_field_type_dict(field_name: str,
                            field_struct: Dict[str, Any],
                            parent_prefix: str) -> NamedTuple:
    """ Constructs a new type based on a provided `field_struct`.
    Literally, transforms a dictionary structure to a named tuple structure.
    """
    if parent_prefix:
        type_name = f'{parent_prefix}_{field_name}'
    else:
        type_name = field_name
    sub_struct = parse(field_struct, type_name)
    field_type = construct_type(type_name, sub_struct)
    return field_type


def clarify_field_type_list(field_name: str,
                            field_struct: List[Any],
                            parent_prefix: str) -> Type[List[Union[Any, NamedTuple]]]:
    """ Clarifies a list type from List to List[T] where T is Any | SomeConcreteType.
    """
    if len(field_struct):
        inner_struct = field_struct[0]
        field_type = clarify_struct_type(field_name, inner_struct, parent_prefix)
        # this is a dynamic signature constructor that mypy won't be able to infer
        return List[field_type]  # type: ignore
    return List[Any]


FIELD_TYPE_CLARIFIERS: Dict[Type, Callable] = {
    str: lambda a, b, c: str,
    int: lambda a, b, c: int,
    float: lambda a, b, c: float,
    bool: lambda a, b, c: bool,
    Optional[Any]: lambda a, b, c: Optional[Any],
    Dict[str, Any]: clarify_field_type_dict,
    List[Any]: clarify_field_type_list,
}


def normalize_name(name: str,
                   pattern=re.compile('^([_0-9]+).*$')) -> Tuple[str, bool]:
    """ Some field name patterns are not allowed in NamedTuples
    https://docs.python.org/3.7/library/collections.html#collections.namedtuple
    """
    if pattern.match(name):
        return f'normalized__{name}', True
    return name, False


def denormalize_name(name: str) -> Tuple[str, bool]:
    """ Undo normalize_name()
    """
    if name.startswith('normalized__'):
        return name[len('normalized__'):], True
    return name, False


def construct_type(name: str, fields: List[Component]) -> NamedTuple:
    """
    :param name: name of the type being constructed
    :param fields: flat sequence of fields the type will have
    :return: a new type based on a NamedTuple
    """
    type_fields: List[Tuple[str, NamedTuple]] = []
    for c in fields:
        # This was not reachable:
        # if c.field_type is Dict[str, Any]:
        #    sub_type_name = inflection.camelize(f'{name}_{c.field_name}')
        #    field_type = construct_type(sub_type_name, c.field_type)
        # else:
        field_type = c.field_type
        type_fields.append((c.field_name, field_type))

    return NamedTuple(inflection.camelize(name), type_fields)


def _maybe_node_for_builtin(typ) -> Optional[col.SchemaNode]:
    try:
        return col.SchemaNode(BUILTIN_TO_SCHEMA_TYPES[typ])
    except KeyError:
        return None


def _maybe_node_for_optional(typ) -> Optional[col.SchemaNode]:
    # typ is Optional[T] where T is either unknown Any or a concrete type
    if typ is Optional[Any]:
        return col.SchemaNode(col.Str(allow_empty=True), missing=None)
    elif insp.get_origin(typ) is Union:
        inner = insp.get_last_args(typ)[0]
        inner_node = decide_node_type(inner)
        inner_node.missing = None
        return inner_node
    return None


def _maybe_node_for_list(typ) -> Optional[col.SequenceSchema]:
    # typ is List[T] where T is either unknown Any or a concrete type
    if typ is List[Any]:
        return col.SequenceSchema(col.SchemaNode(col.Str(allow_empty=True)))
    elif insp.get_origin(typ) is List:
        inner = insp.get_last_args(typ)[0]
        return col.SequenceSchema(decide_node_type(inner))
    return None


def decide_node_type(typ) -> col.SchemaNode:
    # typ is either of:
    #  Union[Type[BuiltinTypes],
    #        Type[Optional[Any]],
    #        Type[List[Any]],
    #        NamedTuple]
    # I'm not adding ^ to the function signature, because mypy
    # is unable to narrow down `typ` to NamedTuple
    # at line type_constructor(typ)
    node = (_maybe_node_for_builtin(typ) or
            _maybe_node_for_optional(typ) or
            _maybe_node_for_list(typ) or
            type_constructor(typ))
    return node


def type_constructor(typ: Type[Tuple]) -> col.SchemaNode:
    constructor = col.SchemaNode(Structure(typ))
    for field_name, field_type in typ.__annotations__.items():
        source_name, __ = denormalize_name(field_name)
        node_type = decide_node_type(field_type)
        node_type.name = source_name
        constructor.add(node_type)
    return constructor


def codegen(typ: Type[Tuple],
            top: bool = True,
            indent: int = 4) -> str:
    ind = ' ' * indent
    code = [f'class {typ.__name__}(NamedTuple):']
    if not typ.__annotations__:
        code.extend([f'{ind}...', '', ''])

    for field_name, field_type in typ.__annotations__.items():
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
        code.extend(['', '',
                     f'Make{typ.__name__} = type_constructor({typ.__name__})'])

        code = ['from typing import NamedTuple, Dict, Any, List, Optional',
                'from typeit import type_constructor', '', ''] + code
    return '\n'.join(code)



class Int(col.Int):

    def serialize(self, node, appstruct):
        """ Default colander integer serializer returns a string representation
        of a number, whereas we want identical representation of the original data.
        """
        r = super().serialize(node, appstruct)
        if r is col.null:
            return r
        return int(r)


class Structure(col.Mapping):

    def __init__(self,
                 typ: Type[Tuple],
                 unknown: str = 'ignore') -> None:
        super().__init__(unknown)
        self.typ = typ

    def deserialize(self, node, cstruct):
        r = super().deserialize(node, cstruct)
        if r is col.null:
            return r
        return self.typ(**{normalize_name(k)[0]: v for k, v in r.items()})

    def serialize(self, node, appstruct: NamedTuple):
        if appstruct is col.null:
            return super().serialize(node, appstruct)
        return super().serialize(
            node,
            {denormalize_name(k)[0]: v for k, v in appstruct._asdict().items()}
        )


BUILTIN_TO_SCHEMA_TYPES = {
    str: col.Str(allow_empty=True),
    int: Int(),
    float: col.Float(),
    bool: col.Bool(),
}