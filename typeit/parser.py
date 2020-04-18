from typing import (
    Type, Tuple, Optional, Any, Union, List, Set,
    Dict, Sequence, get_type_hints,
    MutableSet, TypeVar, FrozenSet, Mapping, Callable,
)

import inspect
import collections

import colander as col
import typing_inspect as insp
from pyrsistent import pmap, pvector
from pyrsistent import typing as pyt

from .compat import Literal
from .definitions import OverridesT
from .utils import is_named_tuple, clone_schema_node
from . import compat
from . import flags
from . import schema
from . import sums
from .schema.meta import TypeExtension
from . import interface as iface


T = TypeVar('T')
MemoType = TypeVar('MemoType')

NoneType = type(None)


OverrideT = Union[
    # flag override
    flags._Flag,
    # new type extension
    TypeExtension,
    Union[
        Mapping[property, str],         # overrides syntax for NamedTuples
        Mapping[Tuple[Type, str], str]  # overrides syntax for dataclasses and init-based hints
    ],
]


def inner_type_boundaries(typ: Type) -> Tuple:
    return insp.get_args(typ, evaluate=True)


def _maybe_node_for_none(
    typ: Union[Type[iface.IType], Any],
    overrides: OverridesT,
    memo: MemoType
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType]:
    if typ is None:
        return _maybe_node_for_literal(Literal[None], overrides, memo)
    return None, memo


def _maybe_node_for_primitive(
    typ: Union[Type[iface.IType], Any],
    overrides: OverridesT,
    memo: MemoType,
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType]:
    """ Check if type could be associated with one of the
    built-in type converters (in terms of Python built-ins).
    """
    registry = schema.primitives.PRIMITIVES_REGISTRY[
        flags.NonStrictPrimitives in overrides
    ]

    try:
        schema_type = registry[typ]
    except KeyError:
        return None, memo

    return schema.nodes.SchemaNode(schema_type), memo


def _maybe_node_for_type_var(
    typ: Type,
    overrides: OverridesT,
    memo: MemoType,
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType]:
    """ When we parse Sequence and List definitions without
    clarified item type, it is possible that this item is defined
    as TypeVar. Since it's an indicator of a generic collection,
    we can treat it as typing.Any.
    """
    if isinstance(typ, TypeVar):
        return _maybe_node_for_primitive(Any, overrides, memo)
    return None, memo


def _maybe_node_for_subclass_based(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType]:
    for subclasses, schema_typ in schema.types.SUBCLASS_BASED_TO_SCHEMA_TYPE.items():
        try:
            is_target = issubclass(typ, subclasses)
        except TypeError:
            # TypeError: issubclass() arg 1 must be a class
            # ``typ`` is not a class, skip the rest
            return None, memo
        else:
            if is_target:
                rv = schema.nodes.SchemaNode(schema_typ(typ, allow_empty=True))
                return rv, memo
    return None, memo


def _maybe_node_for_union(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    supported_type=frozenset({}),
    supported_origin=frozenset({
        Union,
    })
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType]:
    """ Handles cases where typ is a Union, including the special
    case of Optional[Any], which is in essence Union[None, T]
    where T is either unknown Any or a concrete type.
    """
    if typ in supported_type or insp.get_origin(typ) in supported_origin:
        NoneClass = None.__class__
        variants = inner_type_boundaries(typ)
        if variants in ((NoneClass, Any), (Any, NoneClass)):
            # Case for Optional[Any] and Union[None, Any] notations
            rv = schema.nodes.SchemaNode(
                schema.primitives.AcceptEverything(),
                missing=None
            )
            return rv, memo

        allow_empty = NoneClass in variants
        # represents a 2-tuple of (type_from_signature, associated_schema_node)
        variant_nodes: List[Tuple[Type, schema.nodes.SchemaNode]] = []
        for variant in variants:
            if variant is NoneClass:
                continue
            node, memo = decide_node_type(variant, overrides, memo)
            if allow_empty:
                # clonning because we mutate it next, and the node
                # might be already from the cache
                node = clone_schema_node(node)
                node.missing = None
            variant_nodes.append((variant, node))

        primitive_types = schema.primitives.PRIMITIVES_REGISTRY[
            flags.NonStrictPrimitives in overrides
        ]

        union_node = schema.nodes.SchemaNode(
            schema.types.Union(variant_nodes=variant_nodes,
                               primitive_types=primitive_types)
        )
        if allow_empty:
            union_node.missing = None
        return union_node, memo

    return None, memo


def _maybe_node_for_sum_type(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    supported_type=frozenset({}),
    supported_origin=frozenset({})
) -> Optional[schema.nodes.SchemaNode]:
    try:
        matched = issubclass(typ, sums.SumType)
    except TypeError:
        # TypeError: issubclass() arg 1 must be a class
        # ``typ`` is not a class (or a Generic[T] class), skip the rest
        matched = False

    if matched:
        # represents a 2-tuple of (type_from_signature, associated_schema_node)
        variant_nodes: List[Tuple[Type, schema.nodes.SchemaNode]] = []
        for variant in typ:
            node, memo = decide_node_type(
                variant.__variant_meta__.constructor,
                overrides,
                memo
            )
            node.typ.unknown = 'raise'
            variant_nodes.append((variant, node))
        sum_node = schema.nodes.SchemaNode(
            schema.types.Sum(
                typ=typ,
                variant_nodes=variant_nodes,
                as_dict_key=overrides.get(flags.SumTypeDict),
            )
        )
        return sum_node, memo
    return None, memo


def _maybe_node_for_literal(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    supported_type=frozenset({}),
    supported_origin=frozenset({
        Literal,
    }),
    _supported_literal_types=frozenset({
        bool, int, str, bytes, NoneType,
    })
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType]:
    """ Handles cases where typ is a Literal, according to the allowed
    types: https://mypy.readthedocs.io/en/latest/literal_types.html
    """
    if typ in supported_type \
    or insp.get_origin(typ) in supported_origin:
        inner = inner_type_boundaries(typ)
        for x in inner:
            if type(x) not in _supported_literal_types:
                raise TypeError(f'Literals cannot be defined with values of type {type(x)}')
        rv = schema.nodes.SchemaNode(schema.types.Literal(frozenset(inner)))
        return rv, memo
    return None, memo


def _maybe_node_for_list(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    supported_type=frozenset({
        collections.abc.Sequence,
        pyt.PVector,
    }),
    supported_origin=frozenset({
        List,
        Sequence,
        collections.abc.Sequence,
        list,
        pyt.PVector,
    })
) -> Tuple[Optional[col.SequenceSchema], MemoType]:
    # typ is List[T] where T is either unknown Any or a concrete type
    if typ in supported_type or insp.get_origin(typ) in supported_origin:
        try:
            inner = inner_type_boundaries(typ)[0]
        except IndexError:
            inner = Any
        if pyt.PVector in (typ, insp.get_origin(typ)):
            seq_type = schema.nodes.PVectorSchema
        else:
            seq_type = col.SequenceSchema
        node, memo = decide_node_type(inner, overrides, memo)
        return seq_type(node), memo
    return None, memo


def _maybe_node_for_set(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    supported_type=frozenset({
        set,
        frozenset,
        collections.abc.Set,
        collections.abc.MutableSet,
    }),
    supported_origin=frozenset({
        Set,
        MutableSet,
        FrozenSet,
        collections.abc.Set,
        collections.abc.MutableSet,
        set,
        frozenset,
    })
) -> Optional[col.SequenceSchema]:
    origin = insp.get_origin(typ)
    if typ in supported_type or origin in supported_origin:
        try:
            inner = inner_type_boundaries(typ)[0]
        except IndexError:
            inner = Any
        node, memo = decide_node_type(inner, overrides, memo)
        rv = schema.nodes.SetSchema(
            node,
            frozen=(
                typ is frozenset or
                origin in (frozenset, FrozenSet)
            )
        )
        return rv, memo
    return None, memo


def _maybe_node_for_tuple(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    supported_type=frozenset({
        tuple,
    }),
    supported_origin=frozenset({
        tuple, Tuple,
    })
) -> Tuple[Optional[col.TupleSchema], MemoType]:
    if typ in supported_type or insp.get_origin(typ) in supported_origin:
        inner_types = inner_type_boundaries(typ)
        if Ellipsis in inner_types:
            raise TypeError(
                f'You are trying to create a constructor for '
                f'the type "{typ}", however, variable-length tuples '
                f'are not supported by typeit. '
                f'Use Sequence or List if you want to have a '
                f'variable-length collection, and consider '
                f'pyrsistent.pvector for immutability.'
            )
        node = col.TupleSchema()
        # Add tuple elements to the tuple node definition
        for t in inner_types:
            n, memo = decide_node_type(t, overrides, memo)
            node.add(n)
        return node, memo
    return None, memo


def _maybe_node_for_dict(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    supported_type=frozenset({
        collections.abc.Mapping,
        pyt.PMap,
    }),
    supported_origin=frozenset({
        Dict,
        dict,
        collections.abc.Mapping,
        pyt.PMap,
    })
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType]:
    """ This is mainly for cases when a user has manually
    specified that a field should be a dictionary, rather than a
    strict structure, possibly due to dynamic nature of keys
    (for instance, python logging settings that have an infinite
    set of possible attributes).
    """
    if typ in supported_type or insp.get_origin(typ) in supported_origin:
        if pyt.PMap in (typ, insp.get_origin(typ)):
            map_type = schema.nodes.PMapSchema
        else:
            map_type = schema.nodes.DictSchema
        return map_type(), memo
    return None, memo


_type_hints_getter: Callable[[Type], Sequence[Tuple[str, Type]]] = lambda x: list(filter(
    lambda x: x[1] is not NoneType,
    get_type_hints(x).items()
))


def _maybe_node_for_user_type(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType]:
    """ Generates a Colander schema for the given user-defined `typ` that is capable
    of both constructing (deserializing) and serializing the `typ`.
    """
    global_name_overrider: Callable[[str], str] = overrides.get(flags.GlobalNameOverride, flags.Identity)
    is_generic = insp.is_generic_type(typ)

    if is_generic:
        # get the base class that was turned into Generic[T, ...]
        hints_source = insp.get_origin(typ)
        # now we need to map generic type variables to the bound class types,
        # e.g. we map Generic[T,U,V, ...] to actual types of MyClass[int, float, str, ...]
        generic_repr = insp.get_generic_bases(hints_source)
        generic_vars_ordered = (insp.get_args(x)[0] for x in generic_repr)
        bound_type_args = insp.get_args(typ)
        type_var_to_type = pmap(zip(generic_vars_ordered, bound_type_args))
        # resolve type hints
        attribute_hints = [(field_name, type_var_to_type[type_var])
                           for field_name, type_var in _type_hints_getter(hints_source)]
        # Generic types should not have default values
        defaults_source = lambda: ()
        # Overrides should be the same as class-based ones, as Generics are not NamedTuple classes,
        # TODO: consider reducing duplication between this and the logic from init-based types (see below)
        deserialize_overrides = pmap({
            # try to get a specific override for a field, if it doesn't exist, use the global modifier
            overrides.get(
                (typ, python_field_name),
                global_name_overrider(python_field_name)
            ): python_field_name
            for python_field_name, _ in attribute_hints
        })
        # apply a local optimisation that discards `deserialize_overrides`
        # if there is no difference with the original field_names;
        # it is done to occupy less memory with unnecessary mappings
        if deserialize_overrides == pmap({x: x for x, _ in attribute_hints}):
            deserialize_overrides = pmap({})

    elif is_named_tuple(typ):
        hints_source = typ
        attribute_hints = _type_hints_getter(hints_source)
        get_override_identifier = lambda x: getattr(typ, x)
        defaults_source = typ.__new__

        deserialize_overrides = pmap({
            # try to get a specific override for a field, if it doesn't exist, use the global modifier
            overrides.get(
                getattr(typ, python_field_name),
                global_name_overrider(python_field_name)
            ): python_field_name
            for python_field_name in typ._fields
        })

        # apply a local optimisation that discards `deserialize_overrides`
        # if there is no difference with the original field_names;
        # it is done to occupy less memory with unnecessary mappings
        if deserialize_overrides == pmap({x: x for x in typ._fields}):
            deserialize_overrides = pmap({})
    else:
        # use init-based types
        hints_source = typ.__init__
        attribute_hints = _type_hints_getter(hints_source)
        get_override_identifier = lambda x: (typ, x)
        defaults_source = typ.__init__

        deserialize_overrides = pmap({
            # try to get a specific override for a field, if it doesn't exist, use the global modifier
            overrides.get(
                (typ, python_field_name),
                global_name_overrider(python_field_name)
            ): python_field_name
            for python_field_name, _ in attribute_hints
        })
        # apply a local optimisation that discards `deserialize_overrides`
        # if there is no difference with the original field_names;
        # it is done to occupy less memory with unnecessary mappings
        if deserialize_overrides == pmap({x: x for x, _ in attribute_hints}):
            deserialize_overrides = pmap({})

    defaults = {
        k: v.default
        for k, v in inspect.signature(defaults_source).parameters.items()
        if k != 'self' and v.default != inspect.Parameter.empty
    }

    if is_generic and hints_source in overrides:
        # Generic types may have their own custom Schemas defined
        # as a TypeExtension through overrides
        overridden: TypeExtension = overrides[hints_source]
        schema_type_type, _node_children_ = overridden.schema
    else:
        schema_type_type = schema.types.Structure

    schema_type = schema_type_type(
        typ=typ,
        attrs=pvector([x[0] for x in attribute_hints]),
        deserialize_overrides=deserialize_overrides,
    )

    type_schema = schema.nodes.SchemaNode(schema_type)

    for field_name, field_type in attribute_hints:
        globally_modified_field_name = global_name_overrider(field_name)
        # apply field override, if available
        if deserialize_overrides:
            field = get_override_identifier(field_name)
            serialized_field_name = overrides.get(field, globally_modified_field_name)
        else:
            serialized_field_name = globally_modified_field_name

        node, memo = decide_node_type(field_type, overrides, memo)
        if node is None:
            raise TypeError(
                f'Cannot recognise type "{field_type}" of the field '
                f'"{typ.__name__}.{field_name}" (from {typ.__module__})'
            )
        # clonning because we mutate it next, and the node
        # might be from the cache already
        node = clone_schema_node(node)
        node.name = serialized_field_name
        node.missing = defaults.get(field_name, node.missing)
        type_schema.add(node)
    return type_schema, memo


def _maybe_node_for_overridden(
    typ: Type[Any],
    overrides: OverridesT,
    memo: MemoType,
) -> Tuple[Any, MemoType]:
    if typ in overrides:
        override: schema.TypeExtension = overrides[typ]
        schema_type_type, schema_node_children = override.schema
        type_schema = schema.nodes.SchemaNode(schema_type_type())
        for child in schema_node_children:
            type_schema.add(child)
        return type_schema, memo
    return None, memo


PARSING_ORDER = pvector([ _maybe_node_for_overridden
                        , _maybe_node_for_none
                        , _maybe_node_for_primitive
                        , _maybe_node_for_type_var
                        , _maybe_node_for_union
                        , _maybe_node_for_list
                        , _maybe_node_for_tuple
                        , _maybe_node_for_dict
                        , _maybe_node_for_set
                        , _maybe_node_for_literal
                        , _maybe_node_for_sum_type
                        , _maybe_node_for_subclass_based
                        # at this point it could be a user-defined type,
                        # so the parser may do another recursive iteration
                        # through the same plan
                        , _maybe_node_for_user_type
                        ])


CompoundSchema = Union[schema.nodes.SchemaNode, col.TupleSchema, col.SequenceSchema]


def decide_node_type(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType
) -> Tuple[CompoundSchema, MemoType]:
    # typ is either of:
    #  Union[Type[BuiltinTypes],
    #        Type[Optional[Any]],
    #        Type[List[Any]],
    #        Type[Tuple],
    #        Type[Set],
    #        Type[Union[Enum, SumType]],
    #        Type[Dict],
    #        NamedTuple]
    # I'm not adding ^ to the function signature, because mypy
    # is unable to narrow down `typ` to NamedTuple
    # at line _node_for_type(typ)
    if typ in memo:
        return memo[typ], memo
    for attempt_find in PARSING_ORDER:
        node, memo = attempt_find(typ, overrides, memo)
        if node:
            memo = memo.set(typ, node)
            return node, memo
    raise TypeError(
        f'Unable to create a node for "{typ}".'
    )
