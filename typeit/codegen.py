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

import inflection
from pyrsistent import pmap, pvector
from pyrsistent.typing import PMap

from .utils import normalize_name
from .definitions import OverridesT, NO_OVERRIDES
from .definitions import FieldDefinition
from . import interface as iface
from .compat import PY37


def _type_name_getter(typ: Type) -> str:
    return typ.__name__


if PY37:
    # List, Dict, Any... for Python 3.7 (_name)
    def _annotation_name_getter(typ: Type) -> str:
        return typ._name
else:
    # and 3.6(__name__)
    def _annotation_name_getter(typ: Type) -> str:
        return typ.__name__


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


BUILTIN_LITERALS_FOR_TYPES = {
    # Note that we don't have a record for Dict here,
    # because it is clarified to a concrete NamedTuple
    # earlier in the parsing process.
    bool: _type_name_getter,
    int: _type_name_getter,
    float: _type_name_getter,
    str: _type_name_getter,
    List[Any]: _annotation_name_getter,
    # We need explicit [Any] to avoid errors like:
    #   TypeError: Plain typing.Optional is not valid as type argument
    Optional[Any]: lambda __: 'Optional[Any]',
}


LINE_SKIP = ''


def codegen_py(typ: Type[iface.IType],
               overrides: OverridesT = NO_OVERRIDES,
               top: bool = True,
               indent: int = 4) -> Tuple[str, List[str]]:
    """
    :param typ: A type (NamedTuple definition) to generate a source for.
    :param top: flag to indicate that a toplevel structure is to be generated.
        When False, a sub-structure of the toplevel structure is to be generated.
    :param indent: keep indentation for source lines.
    :return:
    """
    overrides_source: List[str] = []

    ind = ' ' * indent
    code = [f'class {typ.__name__}(NamedTuple):']
    hints = get_type_hints(typ)
    if not hints:
        code.extend([
            f'{ind}...',
            LINE_SKIP,
            LINE_SKIP,
        ])

    for field_name, field_type in hints.items():
        # 1. Generate source code for the field
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
                    sub, folded_overrides = codegen_py(field_type, overrides, False)
                    code.insert(0, f'{sub}\n\n')
                    overrides_source.extend(folded_overrides)
            else:
                # field_type: NamedTuple
                # Generate a folded structure definition in the global scope
                # and then use it for the current field
                sub, folded_overrides = codegen_py(field_type, overrides, False)
                code.insert(0, f'{sub}\n\n')
                overrides_source.extend(folded_overrides)

        code.append(f'{ind}{field_name}: {type_literal}')

        # 2. Check if the field included into overrides
        field_override: Optional[str] = overrides.get(getattr(typ, field_name))
        if field_override:
            overrides_source.append(
                f"{ind}{typ.__name__}.{field_name}: '{field_override}',"
            )

    if top:
        if overrides_source:
            overrides_part = [
                LINE_SKIP,
                LINE_SKIP,
                'overrides = {\n' + f'\n'.join(overrides_source) + '\n}',
            ]
            constructor_part = f'type_constructor & overrides ^ {typ.__name__}'
        else:
            overrides_part = []
            constructor_part = f'type_constructor ^ {typ.__name__}'

        code.extend(overrides_part)
        code.extend([
            LINE_SKIP,
            LINE_SKIP,
            f'mk_{inflection.underscore(typ.__name__)}, '
            f'serialize_{inflection.underscore(typ.__name__)} = {constructor_part}',
            LINE_SKIP,
        ])

        code = [
            'from typing import NamedTuple, Dict, Any, List, Optional',
            'from typeit import type_constructor',
            LINE_SKIP,
            LINE_SKIP,
        ] + code
    return '\n'.join(code), overrides_source


def literal_for_type(typ: Type[iface.IType]) -> str:
    # typ is either one of these:
    #   * builtin type
    #   * concrete NamedTuple
    #   * clarified List (i.e. non List[Any])
    try:
        return BUILTIN_LITERALS_FOR_TYPES[typ](typ)
    except KeyError:
        if typ.__class__ is List.__class__:  # type: ignore
            sub_type = literal_for_type(typ.__args__[0])
            return f'List[{sub_type}]'
        # typ: NamedTuple
        return typ.__name__


def typeit(mapping: Mapping[str, Any]) -> Tuple[Type[iface.IType], OverridesT]:
    """
    :param mapping: input struct represented as a mapping
    that needs an equivalent fixed structure.
    """
    structure_fields, overrides = parse(mapping)
    typ, overrides_ = construct_type('main', structure_fields)
    overrides = overrides.update(overrides_)
    return typ, overrides


JSON_TO_BUILTIN_TYPES = {
    True.__class__: bool,
    (0).__class__: int,
    (0.0).__class__: float,
    ''.__class__: str,
    [].__class__: List[Any],
    {}.__class__: Dict[str, Any],
    None.__class__: Optional[Any],
}


def type_for(obj: JsonType) -> Type[JsonType]:
    return JSON_TO_BUILTIN_TYPES[obj.__class__]


def parse(mapping: Mapping[str, Any],
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
    field_type = type_for(field_struct)
    clarifier: ClarifierCallableT = FIELD_TYPE_CLARIFIERS[field_type]
    field_type, overrides = clarifier(field_name, field_struct, parent_prefix)
    return field_type, overrides


def _clarify_field_type_dict(field_name: str,
                             field_struct: Dict[str, Any],
                             parent_prefix: str) -> Tuple[Type[iface.IType], OverridesT]:
    """ Constructs a new type based on a provided `field_struct`.
    Literally, transforms a dictionary structure to a named tuple structure.
    """
    if parent_prefix:
        type_name = f'{parent_prefix}_{field_name}'
    else:
        type_name = field_name
    sub_struct, overrides = parse(field_struct, type_name)
    field_type, overrides_ = construct_type(type_name, sub_struct)
    overrides = overrides.update(overrides_)
    return field_type, overrides


def _clarify_field_type_list(field_name: str,
                             field_struct: List[Any],
                             parent_prefix: str) -> Tuple[Type[List[Union[Any, iface.IType]]],
                                                          OverridesT]:
    """ Clarifies a list type from List to List[T] where T is Any | SomeConcreteType.
    """
    if len(field_struct):
        inner_struct = field_struct[0]
        field_type, overrides = clarify_struct_type(field_name, inner_struct, parent_prefix)
        # this is a dynamic signature constructor that mypy won't be able to infer
        return List[field_type], overrides  # type: ignore
    return List[Any], NO_OVERRIDES


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
    Dict[str, Any]: _clarify_field_type_dict,
    List[Any]: _clarify_field_type_list,
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

    typ = NamedTuple(inflection.camelize(name), type_fields)  # type: ignore
    type_overrides: PMap[property, str] = pmap({
        getattr(typ, k): v for k, v in overrides.items()
    })
    return typ, type_overrides  # type: ignore
