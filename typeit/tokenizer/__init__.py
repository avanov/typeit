""" Tokenizer is useful for translating nested declarations from one representation into another.
For instance, a composition of python types can be translated into a GraphQL query, as the latter
is represented in a nested format, too.
"""
from typing import Type, Any, NamedTuple, Generator, Union, get_type_hints

from ..codegen import _type_name_getter
from ..combinator.constructor import TypeConstructor, _TypeConstructor
from ..schema import nodes
from ..schema import types as node_types


class Primitive(NamedTuple):
    pass


class Sequence(NamedTuple):
    pass


class Structure(NamedTuple):
    pass


class Custom(NamedTuple):
    pass


TypeShape = Union[Primitive, Sequence, Structure, Custom]


class BeginType(NamedTuple):
    shape: TypeShape
    python_name: str
    docstring: str


class EndType(NamedTuple):
    pass


class BeginAttribute(NamedTuple):
    python_name: str
    wire_name: str
    python_type: Type[Any]
    wire_type: Any


class EndAttribute(NamedTuple):
    pass


Token = Union[BeginType, EndType, BeginAttribute, EndAttribute]


def iter_tokens(typ: Type[Any], typer: _TypeConstructor = TypeConstructor) -> Generator[Token, None, None]:
    try:
        typ_schema = typer.memo[typ]
    except KeyError:
        _ = typer ^ typ
        typ_schema = typer.memo[typ]

    if isinstance(typ_schema, nodes.SchemaNode):
        shape: TypeShape = Structure()
    elif isinstance(typ_schema, (nodes.TupleSchema, nodes.SequenceSchema)):
        shape = Sequence()
    else:
        raise NotImplementedError(f'Shape needed for {type(typ_schema)}')

    yield BeginType(
        shape=shape,
        python_name=_type_name_getter(typ),
        docstring=typ.__doc__ or 'no docs provided yet'
    )
    if isinstance(shape, Structure):
        yield from iter_schema_node(typ_schema)
    else:
        yield from iter_sequence_node(typ_schema)

    yield EndType()


def iter_schema_node(typ_schema: nodes.SchemaNode,
                     typer: _TypeConstructor = TypeConstructor) -> Generator[Token, None, None]:
    meta_source: node_types.Structure = typ_schema.typ
    python_parent_type = meta_source.typ
    python_parent_hints = get_type_hints(python_parent_type)


    for schema_attr in typ_schema.children:
        if isinstance(schema_attr, nodes.SchemaNode):
            if schema_attr.children:
                is_compound = True
                attribute_node = schema_attr
                try:
                    wire_type = get_type_hints(attribute_node.typ.serialize)['return']
                except KeyError:
                    raise TypeError(f'Please specify a return type of {attribute_node.typ.serialize}()')
            else:
                # attribute is a primitive type
                is_compound = False
                attribute_node = schema_attr
                try:
                    wire_type = get_type_hints(attribute_node.typ.serialize)['return']
                except KeyError:
                    raise TypeError(f'Please specify a return type of {attribute_node.typ.serialize}()')

        elif isinstance(schema_attr, nodes.SequenceSchema):
            is_compound = True
            # attribute is a compound type and we're going to have a nested BeginType
            attribute_node = schema_attr.children[0]
            try:
                wire_type = get_type_hints(attribute_node.typ.serialize)['return']
            except KeyError:
                raise TypeError(f'Please specify a return type of {attribute_node.typ.serialize}()')
        else:
            raise NotImplementedError(f'Probably missing handler for schema type {type(schema_attr)}')

        wire_name = meta_source.serialize_overrides.get(schema_attr.name, schema_attr.name)
        py_name = meta_source.deserialize_overrides.get(schema_attr.name, schema_attr.name)
        token = BeginAttribute(
            python_name=schema_attr.name,
            wire_name=wire_name,
            python_type=python_parent_hints[py_name],
            wire_type=wire_type,
        )
        yield token

        if is_compound:
            attr_python_type = attribute_node.typ.typ
            yield from iter_tokens(attr_python_type, typer)

        yield EndAttribute()


def iter_sequence_node(typ_schema: Union[nodes.SequenceSchema, nodes.TupleSchema]) -> Generator[Token, None, None]:
    return
