from typing import (
    Type,
    Tuple,
    get_type_hints,
    List,
    Any,
    Optional,
    Dict,
    NamedTuple,
    Union,
    Callable,
    Mapping,
    Sequence,
)

import typing_inspect as insp
import inflection
from pyrsistent import pmap, pvector
from pyrsistent.typing import PMap

from typeit.interface import INamedTuple, IType
from .utils import normalize_name
from .definitions import OverridesT, NO_OVERRIDES
from .definitions import FieldDefinition
from . import interface as iface
from .compat import PY37


def _type_name_getter(typ: Type[IType]) -> str:
    return typ.__name__


if PY37:
    # List, Dict, Any... for Python 3.7 (_name)
    def _annotation_name_getter(typ: Type[INamedTuple]) -> str:
        return typ._name
else:
    # and 3.6(__name__)
    def _annotation_name_getter(typ: Type[IType]) -> str:
        return typ.__name__


BuiltinTypes = Union[
    bool,
    int,
    float,
    str,
]


PythonPrimitives = frozenset(insp.get_args(BuiltinTypes) + (None,))


JsonType = Union[
    BuiltinTypes,
    Sequence[Any],
    Mapping[str, Any],
    None
]


# A sum of all types that Parser and Codegen need to support
ParseableType = Union[Type[JsonType], Type[iface.IType]]


BUILTIN_LITERALS_FOR_TYPES = {
    # Note that we don't have a record for Dict/Mapping here,
    # because it is clarified to a concrete NamedTuple
    # earlier in the parsing process.
    bool: _type_name_getter,
    int: _type_name_getter,
    float: _type_name_getter,
    str: _type_name_getter,
    List[Any]: _annotation_name_getter,
    Sequence[Any]: _annotation_name_getter,
    # We need explicit [Any] to avoid errors like:
    #   TypeError: Plain typing.Optional is not valid as type argument
    Optional[Any]: lambda __: 'Optional[Any]',
    Any: 'Any',
}


LINE_SKIP = ''
NEW_LINE = '\n'


class TypeitSchema(NamedTuple):
    typ: ParseableType = None
    overrides: OverridesT = NO_OVERRIDES
    sequence_wrappers: int = 0


def codegen_py(typeit_schema: TypeitSchema,
               top: bool = True,
               indent: int = 4) -> Tuple[str, Sequence[str]]:
    """
    :param typ: A type (NamedTuple definition) to generate a source for.
    :param top: flag to indicate that a toplevel structure is to be generated.
        When False, a sub-structure of the toplevel structure is to be generated.
    :param indent: keep indentation for source lines.
    :return:
    """
    typ = typeit_schema.typ
    overrides = typeit_schema.overrides
    wrappers = typeit_schema.sequence_wrappers

    overrides_source: List[str] = []
    if typ is None:
        type_name = 'None'
    elif typ is Any:
        type_name = 'Any'
    else:
        type_name = typ.__name__

    required_imports = [
        'from typing import Any, NamedTuple, Optional, Sequence',
    ]
    wrapped_type_literal = ('Sequence[' * wrappers) + type_name + (']' * wrappers)

    if typ in PythonPrimitives:
        required_imports.extend([
            'from typeit import type_constructor',
        ])
        if wrappers:
            generated_definitions = [
                f'Main = {wrapped_type_literal}'
            ]
        else:
            generated_definitions = []


    elif typ is Any:
        required_imports.extend([
            'from typeit import type_constructor',
        ])
        generated_definitions = [
            f'Main = {wrapped_type_literal}'
        ]

    else:
        required_imports.extend([
            'from typeit import type_constructor',
        ])
        ind = ' ' * indent
        generated_definitions = [f'class {type_name}(NamedTuple):']
        hints = get_type_hints(typ)
        if not hints:
            generated_definitions.extend([
                f'{ind}...',
                LINE_SKIP,
                LINE_SKIP,
            ])

        for field_name, field_type in hints.items():
            # 1. Generate source code for the field
            type_literal = literal_for_type(field_type)
            if field_type not in BUILTIN_LITERALS_FOR_TYPES:
                # field_type: Union[NamedTuple, Sequence]
                # TODO: Sequence/List/PVector flag-based
                folded_lists_count = type_literal.count('Sequence[')
                if folded_lists_count:
                    # field_type: Sequence[T]
                    # traverse to the folded object
                    for __ in range(folded_lists_count):
                        field_type = field_type.__args__[0]

                    if field_type not in BUILTIN_LITERALS_FOR_TYPES:
                        sub, folded_overrides = codegen_py(
                            TypeitSchema(field_type, overrides, wrappers), False
                        )
                        generated_definitions.insert(0, f'{sub}{NEW_LINE}{NEW_LINE}')
                        overrides_source.extend(folded_overrides)
                else:
                    # field_type: NamedTuple
                    # Generate a folded structure definition in the global scope
                    # and then use it for the current field
                    sub, folded_overrides = codegen_py(
                        TypeitSchema(field_type, overrides, wrappers), False
                    )
                    generated_definitions.insert(0, f'{sub}{NEW_LINE}{NEW_LINE}')
                    overrides_source.extend(folded_overrides)

            generated_definitions.append(f'{ind}{field_name}: {type_literal}')

            # 2. Check if the field included into overrides
            field_override: Optional[str] = overrides.get(getattr(typ, field_name))
            if field_override:
                overrides_source.append(
                    f"{ind}{type_name}.{field_name}: '{field_override}',"
                )

    if top:
        if wrappers:
            type_literal = 'Main'
        else:
            type_literal = type_name
        if overrides_source:
            overrides_part = [
                LINE_SKIP,
                LINE_SKIP,
                'overrides = {' +
                NEW_LINE +
                NEW_LINE.join(overrides_source) +
                NEW_LINE +
                '}'
            ]
            constructor_part = f'type_constructor & overrides ^ {type_literal}'
        else:
            overrides_part = []
            constructor_part = f'type_constructor ^ {type_literal}'

        generated_definitions.extend(overrides_part)
        constructor_serializer_def = (
            f'mk_{inflection.underscore(type_literal)}, '
            f'serialize_{inflection.underscore(type_literal)} = {constructor_part}'
        )
        generated_definitions.extend([
            LINE_SKIP,
            constructor_serializer_def,
            LINE_SKIP,
        ])

        # TODO: import Sequence/List/PVector flag-based
        generated_definitions = ( required_imports
                                + [LINE_SKIP]
                                + generated_definitions )
    return NEW_LINE.join(generated_definitions), overrides_source


def literal_for_type(typ: Type[iface.IType]) -> str:
    # typ is either one of these:
    #   * builtin type
    #   * concrete NamedTuple
    #   * clarified List (i.e. non List[Any])
    try:
        return BUILTIN_LITERALS_FOR_TYPES[typ](typ)
    except KeyError:
        if typ.__class__ in {List.__class__, Sequence.__class__}:  # type: ignore
            sub_type = literal_for_type(typ.__args__[0])
            # TODO: Sequence/List/PVector flag-based
            return f'Sequence[{sub_type}]'
        # typ: NamedTuple
        return typ.__name__


def typeit(
    python_data: JsonType
) -> TypeitSchema:
    """
    :param python_data: input structure as a combination of
    builtin python data types, that needs an equivalent fixed structure.
    """
    if python_data is None:
        return TypeitSchema()

    # when python_data is a list, we need to find the underlying
    # non-sequential data type (if any).
    underlying_data, depth = traverse_non_sequence(python_data)
    if underlying_data is None:
        data_type = Any
    else:
        data_type = typing_for(underlying_data)

    if data_type is Any or data_type in PythonPrimitives:
        return TypeitSchema(typ=data_type,
                            sequence_wrappers=depth)

    # Only mapping is left at this point
    structure_fields, overrides = parse_mapping(underlying_data)
    typ, overrides_ = construct_type('main', structure_fields)
    overrides = overrides.update(overrides_)
    return TypeitSchema(typ=typ, sequence_wrappers=depth, overrides=overrides)


def traverse_non_sequence(data: Sequence[Any]) -> Tuple[Optional[Any], int]:
    is_seq = isinstance(data, list)
    seq_len = len(data) if is_seq else 0
    if is_seq:
        if seq_len:
            t, c = traverse_non_sequence(data[0])
            return t, c + 1
        return None, 1
    return data, 0


JSON_TO_BUILTIN_TYPING: Mapping[Type, Type] = {
    True.__class__: bool,
    (0).__class__: int,
    (0.0).__class__: float,
    ''.__class__: str,
    [].__class__: Sequence[Any],
    {}.__class__: Mapping[str, Any],
    None.__class__: Optional[Any],
}


def typing_for(obj: JsonType) -> Type:
    """ Return a typing reference type for a given JsonType
    """
    return JSON_TO_BUILTIN_TYPING[obj.__class__]


def parse_mapping(mapping: Mapping[str, Any],
                  parent_prefix: str = '') -> Tuple[Sequence[FieldDefinition], OverridesT]:
    """ Dictionary Parser entry point.
    """
    definitions: List[FieldDefinition] = []
    overrides: OverridesT = NO_OVERRIDES
    for source_name, field_struct in mapping.items():
        field_name = normalize_name(source_name)
        field_type, overrides_ = clarify_struct_type(field_name, field_struct, parent_prefix)
        overrides = overrides.update(overrides_)
        definitions.append(FieldDefinition(source_name=source_name,
                                           field_name=field_name,
                                           field_type=field_type))
    return pvector(definitions), overrides


def clarify_struct_type(field_name: str,
                        field_struct: Any,
                        parent_prefix: str) -> Tuple[Type[iface.IType], OverridesT]:
    field_type = typing_for(field_struct)
    clarifier: ClarifierCallableT = FIELD_TYPE_CLARIFIERS[field_type]
    field_type, overrides = clarifier(field_name, field_struct, parent_prefix)
    return field_type, overrides


def _clarify_field_type_dict(field_name: str,
                             field_struct: Dict[str, Any],
                             parent_prefix: str) -> Tuple[Type[iface.IType], OverridesT]:
    """ Constructs a new type based on the provided `field_struct`.
    Literally, transforms a dictionary structure to a named tuple structure.
    """
    if parent_prefix:
        type_name = f'{parent_prefix}_{field_name}'
    else:
        type_name = field_name
    sub_struct, overrides = parse_mapping(field_struct, type_name)
    field_type, overrides_ = construct_type(type_name, sub_struct)
    overrides = overrides.update(overrides_)
    return field_type, overrides


def _clarify_field_type_list(field_name: str,
                             field_struct: Sequence[Any],
                             parent_prefix: str) -> Tuple[Type[List[Union[Any, iface.IType]]],
                                                          OverridesT]:
    """ Clarifies a list type from List to List[T] where T is Any | SomeConcreteType.
    """
    if len(field_struct):
        inner_struct = field_struct[0]
        field_type, overrides = clarify_struct_type(field_name, inner_struct, parent_prefix)
        # this is a dynamic signature constructor that mypy won't be able to infer
        return Sequence[field_type], overrides  # type: ignore
    return Sequence[Any], NO_OVERRIDES


ClarifierCallableT = Callable[[str, Any, str], Tuple[Type, OverridesT]]


FIELD_TYPE_CLARIFIERS: Mapping[Type, ClarifierCallableT] = {
    # primitive types will not have overrides,
    # because there's no field mapping in them
    str: lambda a, b, c: (str, NO_OVERRIDES),
    int: lambda a, b, c: (int, NO_OVERRIDES),
    float: lambda a, b, c: (float, NO_OVERRIDES),
    bool: lambda a, b, c: (bool, NO_OVERRIDES),
    # typeit does not provide non-Any optionals in codegen functionality,
    # because that would require traversing and probing values through
    # available sample data. Technically it is possible,
    # but I was too lazy to implement it.
    Optional[Any]: lambda a, b, c: (Optional[Any], NO_OVERRIDES),
    Mapping[str, Any]: _clarify_field_type_dict,
    Sequence[Any]: _clarify_field_type_list,
}


def construct_type(name: str,
                   fields: Sequence[FieldDefinition]) -> Tuple[Type, OverridesT]:
    """ Generates a NamedTuple type structure out of provided
    field definitions.

    :param name: name of the type being constructed
    :param fields: flat sequence of fields the type will have
    :return: a new type based on a NamedTuple and its overrides
    """
    type_fields: List[Tuple[str, NamedTuple]] = []
    overrides: Dict[str, str] = {}

    for c in fields:
        field_type = c.field_type
        type_fields.append((c.field_name, field_type))
        if c.field_name != c.source_name:
            overrides[c.field_name] = c.source_name

    typ = NamedTuple(inflection.camelize(name), type_fields)
    type_overrides: PMap[property, str] = pmap({
        getattr(typ, k): v for k, v in overrides.items()
    })
    return typ, type_overrides
