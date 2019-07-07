from typing import (
    Type, Tuple, Optional, Any, Union, List, Set,
    Dict, Sequence, get_type_hints,
    MutableSet, TypeVar, FrozenSet, Mapping,
)

from pyrsistent.typing import PMap
from typing_extensions import Literal
import collections

import colander as col
import typing_inspect as insp
from pyrsistent import pmap, pvector
from pyrsistent import typing as pyt

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
    Mapping[property, str],
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
        flags.NON_STRICT_PRIMITIVES in overrides
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
            flags.NON_STRICT_PRIMITIVES in overrides
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
    if issubclass(typ, sums.SumType):
        # represents a 2-tuple of (type_from_signature, associated_schema_node)
        variant_nodes: List[Tuple[Type, schema.nodes.SchemaNode]] = []
        for variant in typ:
            node, memo = decide_node_type(
                variant.__variant_meta__.constructor,
                overrides,
                memo
            )
            variant_nodes.append((variant, node))
        sum_node = schema.nodes.SchemaNode(
            schema.types.Sum(
                typ=typ,
                variant_nodes=variant_nodes,
                as_dict_key=overrides.get(flags.SUM_TYPE_DICT),
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
        insp.get_generic_type(Literal)  # py3.6 fix
    }),
    _supported_literal_types=frozenset({
        bool, int, str, bytes, NoneType,
    })
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType]:
    """ Handles cases where typ is a Literal, according to the allowed
    types: https://mypy.readthedocs.io/en/latest/literal_types.html
    """
    if typ in supported_type \
    or insp.get_origin(typ) in supported_origin \
    or (compat.PY36 and insp.get_generic_type(typ) in supported_origin):
        inner = inner_type_boundaries(typ) if not compat.PY36 else typ.__values__
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
            # In case of a non-clarified collection
            # (collection without defined item type),
            # Python 3.6 will have empty inner type,
            # whereas Python 3.7 will contain a single TypeVar.
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
            # In case of a non-clarified set (set without defined collection item type),
            # Python 3.6 will have empty inner type,
            # whereas Python 3.7 will contain a single TypeVar.
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
        Mapping,  # py3.6
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


def _maybe_node_for_user_type(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType]:
    """ Generates a Colander schema for the given `typ` that is capable
    of both constructing (deserializing) and serializing the `typ`.
    """
    if is_named_tuple(typ):
        deserialize_overrides = pmap({
            overrides[getattr(typ, x)]: x
            for x in typ._fields
            if getattr(typ, x) in overrides
        })
        hints_source = typ
    else:
        # use init-based types;
        # note that overrides are not going to work without named tuples
        deserialize_overrides = pmap({})
        hints_source = typ.__init__

    attribute_hints = list(filter(
        lambda x: x[1] is not NoneType,
        get_type_hints(hints_source).items()
    ))

    type_schema = schema.nodes.SchemaNode(
        schema.types.Structure(
            typ=typ,
            overrides=overrides,
            attrs=pvector([x[0] for x in attribute_hints]),
            deserialize_overrides=deserialize_overrides,
        )
    )

    for field_name, field_type in attribute_hints:
        # apply field override, if available
        if deserialize_overrides:
            field = getattr(typ, field_name)
            serialized_field_name = overrides.get(field, field_name)
        else:
            serialized_field_name = field_name

        node, memo = decide_node_type(field_type, overrides, memo)
        if node is None:
            raise TypeError(
                f'Cannot recognise type "{field_type}" of the field '
                f'"{typ.__name__}.{field_name}" (from {typ.__module__})'
            )
        # clonning because we mutate it next, and the node
        # might be already from the cache
        node = clone_schema_node(node)
        node.name = serialized_field_name
        type_schema.add(node)
    return type_schema, memo


def _maybe_node_for_overridden(
    typ: Type[Any],
    overrides: OverridesT,
    memo: MemoType,
) -> Tuple[Any, MemoType]:
    if typ in overrides:
        override: schema.TypeExtension = overrides[typ]
        return override.schema, memo
    return None, memo


PARSING_ORDER = [ _maybe_node_for_overridden
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
                , _maybe_node_for_user_type ]


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
