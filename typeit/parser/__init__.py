from typing import (
    Type, Tuple, Optional, Any, Union, List, Set,
    Dict, Sequence, get_type_hints,
    MutableSet, TypeVar, FrozenSet, Mapping, Callable, NamedTuple, ForwardRef, NewType,
)

import inspect
import collections

import typing_inspect as insp
from pyrsistent import pmap, pvector
from pyrsistent import typing as pyt

from ..compat import Literal
from ..definitions import OverridesT
from ..utils import is_named_tuple, clone_schema_node, get_global_name_overrider
from .. import flags
from .. import schema
from .. import sums
from ..schema.meta import TypeExtension
from .. import interface as iface


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


ForwardRefs = Dict[ForwardRef, Optional[schema.nodes.SchemaNode]]


def _maybe_node_for_none(
    typ: Union[Type[iface.IType], Any],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs,
    supported_type: FrozenSet = frozenset([
        None,
        Type[None]  # special case to support MyPy aliases of None https://github.com/python/mypy/pull/3754
    ])
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType, ForwardRefs]:
    if typ in supported_type:
        return _maybe_node_for_literal(Literal[None], overrides, memo, forward_refs)
    return None, memo, forward_refs


def _maybe_node_for_forward_ref(
    typ: Union[ForwardRef, Any],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType, ForwardRefs]:
    if isinstance(typ, ForwardRef):
        schema_type = schema.types.ForwardReferenceType(forward_ref=typ, ref_registry=forward_refs)
        forward_refs[typ] = None
        return schema.nodes.SchemaNode(schema_type), memo, forward_refs
    return None, memo, forward_refs


def _maybe_node_for_newtype(
    typ: Union[NewType, Any],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType, ForwardRefs]:
    """ newtypes do not change the underlying runtime data type that is used in
    calls like isinstance(), therefore it's just enough for us to find
    a schema node of the underlying type
    """
    rv = None
    if insp.is_new_type(typ):
        return decide_node_type(typ.__supertype__, overrides, memo, forward_refs)
    return rv, memo, forward_refs


def _maybe_node_for_primitive(
    typ: Union[Type[iface.IType], Any],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType, ForwardRefs]:
    """ Check if type could be associated with one of the
    built-in type converters (in terms of Python built-ins).
    """
    registry = schema.primitives.PRIMITIVES_REGISTRY[
        flags.NonStrictPrimitives in overrides
    ]

    try:
        schema_type = registry[typ]
    except KeyError:
        return None, memo, forward_refs

    return schema.nodes.SchemaNode(schema_type), memo, forward_refs


def _maybe_node_for_type_var(
    typ: Type,
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType, ForwardRefs]:
    """ When we parse Sequence and List definitions without
    clarified item type, it is possible that this item is defined
    as TypeVar. Since it's an indicator of a generic collection,
    we can treat it as typing.Any.
    """
    if isinstance(typ, TypeVar):
        return _maybe_node_for_primitive(Any, overrides, memo, forward_refs)
    return None, memo, forward_refs


def _maybe_node_for_subclass_based(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType, ForwardRefs]:
    rv = None
    for subclasses, schema_typ in schema.types.SUBCLASS_BASED_TO_SCHEMA_TYPE.items():
        try:
            is_target = issubclass(typ, subclasses)
        except TypeError:
            # TypeError: issubclass() arg 1 must be a class
            # ``typ`` is not a class, skip the rest
            break
        else:
            if is_target:
                rv = schema.nodes.SchemaNode(schema_typ(typ, allow_empty=True))
                break

    return rv, memo, forward_refs


def _maybe_node_for_union(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs,
    supported_type=frozenset({}),
    supported_origin=frozenset({
        Union,
    })
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType, ForwardRefs]:
    """ Handles cases where typ is a Union, including the special
    case of Optional[Any], which is in essence Union[None, T]
    where T is either unknown Any or a concrete type.
    """
    if typ in supported_type or get_origin_39(typ) in supported_origin:
        variants = inner_type_boundaries(typ)
        if variants in ((NoneType, Any), (Any, NoneType)):
            # Case for Optional[Any] and Union[None, Any] notations
            rv = schema.nodes.SchemaNode(
                schema.primitives.AcceptEverything(),
                missing=None
            )
            return rv, memo, forward_refs

        allow_empty = NoneType in variants
        # represents a 2-tuple of (type_from_signature, associated_schema_node)
        variant_nodes: List[Tuple[Type, schema.nodes.SchemaNode]] = []
        for variant in variants:
            if variant is NoneType:
                continue
            node, memo, forward_refs = decide_node_type(variant, overrides, memo, forward_refs)
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
        return union_node, memo, forward_refs

    return None, memo, forward_refs


def _maybe_node_for_sum_type(
    typ: Union[Type[iface.IType], Type[sums.SumType]],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs,
    supported_type=frozenset({}),
    supported_origin=frozenset({})
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType, ForwardRefs]:
    try:
        matched = issubclass(typ, sums.SumType)
    except TypeError:
        # TypeError: issubclass() arg 1 must be a class
        # ``typ`` is not a class (or a Generic[T] class), skip the rest
        matched = False

    sum_node = None
    if matched:
        # represents a 2-tuple of (type_from_signature, associated_schema_node)
        variant_nodes: List[Tuple[Type, schema.nodes.SchemaNode]] = []
        for variant in typ:
            node, memo, forward_refs = decide_node_type(
                variant.__variant_meta__.constructor,
                overrides,
                memo,
                forward_refs
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
    return sum_node, memo, forward_refs


def _maybe_node_for_literal(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs,
    supported_type=frozenset({}),
    supported_origin=frozenset({
        Literal,
    }),
    _supported_literal_types=frozenset({
        bool, int, str, bytes, NoneType,
    })
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType, ForwardRefs]:
    """ Handles cases where typ is a Literal, according to the allowed
    types: https://mypy.readthedocs.io/en/latest/literal_types.html
    """
    rv = None
    if typ in supported_type \
    or get_origin_39(typ) in supported_origin:
        inner = inner_type_boundaries(typ)
        for x in inner:
            if type(x) not in _supported_literal_types:
                raise TypeError(f'Literals cannot be defined with values of type {type(x)}')
        rv = schema.nodes.SchemaNode(schema.types.Literal(frozenset(inner)))
    return rv, memo, forward_refs


def _maybe_node_for_sequence(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs,
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
) -> Tuple[Optional[schema.nodes.SequenceSchema], MemoType, ForwardRefs]:
    rv = None
    # typ is List[T] where T is either unknown Any or a concrete type
    if typ in supported_type or get_origin_39(typ) in supported_origin:
        try:
            inner = inner_type_boundaries(typ)[0]
        except IndexError:
            # Python 3.9 access to arguments
            try:
                inner = typ.__args__[0]
            except (AttributeError, IndexError):
                inner = Any
        if pyt.PVector in (typ, get_origin_39(typ)):
            seq_type = schema.nodes.PVectorSchema
        else:
            seq_type = schema.nodes.SequenceSchema
        node, memo, forward_refs = decide_node_type(inner, overrides, memo, forward_refs)
        rv = seq_type(node)
    return rv, memo, forward_refs


def get_origin_39(typ: Type[Any]) -> Type[Any]:
    """python3.9 aware origin"""
    origin = insp.get_origin(typ)
    if origin is None:
        origin = typ.__origin__ if hasattr(typ, '__origin__') else None
    return origin


def _maybe_node_for_set(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs,
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
) -> Tuple[Optional[schema.nodes.SequenceSchema], MemoType, ForwardRefs]:
    rv = None
    origin = get_origin_39(typ)
    if typ in supported_type or origin in supported_origin:
        try:
            inner = inner_type_boundaries(typ)[0]
        except IndexError:
            inner = Any
        node, memo, forward_refs = decide_node_type(inner, overrides, memo, forward_refs)
        rv = schema.nodes.SetSchema(
            node,
            frozen=(
                typ is frozenset or
                origin in (frozenset, FrozenSet)
            )
        )
    return rv, memo, forward_refs


def _maybe_node_for_tuple(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs,
    supported_type=frozenset({
        tuple,
    }),
    supported_origin=frozenset({
        tuple, Tuple,
    })
) -> Tuple[Optional[schema.nodes.TupleSchema], MemoType, ForwardRefs]:
    rv = None
    if typ in supported_type or get_origin_39(typ) in supported_origin:
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
        node = schema.nodes.TupleSchema()
        # Add tuple elements to the tuple node definition
        for t in inner_types:
            n, memo, forward_refs = decide_node_type(t, overrides, memo, forward_refs)
            node.add(n)
        rv = node

    return rv, memo, forward_refs


def are_generic_bases_match(bases, template) -> bool:
    for base in bases:
        if base in template:
            return True
    return False


def is_pmap(typ: Type[Any]) -> bool:
    """python3.9 compatible pmap checker"""
    return pyt.PMap in (typ, get_origin_39(typ)) \
        or (hasattr(typ, '__name__') and typ.__name__ == "PMap" and typ.__module__.startswith("pyrsistent."))


def is_39_deprecated_dict(typ: Type[Any]) -> bool:
    """python3.9 deprecated Dict in favor of dict, and now it lacks necessary metadata other than name and module if
    there is no other constraints on key and value types, e.g. Dict[Key, Val] can be recognised, however just Dict cannot be.
    """
    return get_origin_39(typ) is None and hasattr(typ, '_name') and typ._name == 'Dict' and typ.__module__ == 'typing'


def _maybe_node_for_dict(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs,
    supported_type=frozenset({
        dict,
        collections.abc.Mapping,
        pyt.PMap,
    }),
    supported_origin=frozenset({
        Dict,
        dict,
        collections.abc.Mapping,
        pyt.PMap,
    })
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType, ForwardRefs]:
    """ This is mainly for cases when a user has manually
    specified that a field should be a dictionary, rather than a
    strict structure, possibly due to dynamic nature of keys
    (for instance, python logging settings that have an infinite
    set of possible attributes).
    """
    rv = None
    # This is a hack for Python 3.9
    if insp.is_generic_type(typ):
        generic_bases = [get_origin_39(x) for x in insp.get_generic_bases(typ)]
    else:
        generic_bases = []

    typ = dict if is_39_deprecated_dict(typ) else typ

    if typ in supported_type or get_origin_39(typ) in supported_origin or are_generic_bases_match(generic_bases, supported_origin):
        schema_node_type = schema.nodes.PMapSchema if is_pmap(typ) else schema.nodes.SchemaNode

        if generic_bases:
            # python 3.9 args
            key_type, value_type = typ.__args__
        else:
            try:
                key_type, value_type = insp.get_args(typ)
            except ValueError:
                # Mapping doesn't provide key/value types
                key_type, value_type = Any, Any

        key_node,   memo, forward_refs = decide_node_type(key_type, overrides, memo, forward_refs)
        value_node, memo, forward_refs = decide_node_type(value_type, overrides, memo, forward_refs)
        mapping_type = schema.types.TypedMapping(key_node=key_node, value_node=value_node)
        rv = schema_node_type(mapping_type)
    return rv, memo, forward_refs


class AttrInfo(NamedTuple):
    name: str
    resolved_type: Type
    raw_type: Union[Type, ForwardRef]


def _type_hints_getter(typ: Type) -> Sequence[AttrInfo]:
    raw = getattr(typ, '__annotations__', {})
    existing_only = lambda x: x[1] is not NoneType
    return [AttrInfo(name, t, raw.get(name, t)) for name, t in filter(existing_only, get_type_hints(typ).items())]


def _maybe_node_for_user_type(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs,
) -> Tuple[Optional[schema.nodes.SchemaNode], MemoType, ForwardRefs]:
    """ Generates a Colander schema for the given user-defined `typ` that is capable
    of both constructing (deserializing) and serializing the `typ`.
    This includes named tuples and dataclasses.
    """
    global_name_overrider = get_global_name_overrider(overrides)
    is_generic = insp.is_generic_type(typ)

    if is_generic:
        # get the base class that was turned into Generic[T, ...]
        hints_source = get_origin_39(typ)
        # now we need to map generic type variables to the bound class types,
        # e.g. we map Generic[T,U,V, ...] to actual types of MyClass[int, float, str, ...]
        generic_repr = insp.get_generic_bases(hints_source)
        generic_vars_ordered = (insp.get_args(x)[0] for x in generic_repr)
        bound_type_args = insp.get_args(typ)
        type_var_to_type = pmap(zip(generic_vars_ordered, bound_type_args))
        # resolve type hints
        attribute_hints = [(field_name, type_var_to_type[type_var])
                           for field_name, type_var in ((x, raw_type) for x, _resolved_type, raw_type in _type_hints_getter(hints_source))]
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
        attribute_hints = [(x, raw_type) for x, y, raw_type in _type_hints_getter(hints_source)]
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
        attribute_hints = [(x, raw_type) for x, y, raw_type in _type_hints_getter(hints_source)]
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

        node, memo, forward_refs = decide_node_type(field_type, overrides, memo, forward_refs)
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
    return type_schema, memo, forward_refs


def _maybe_node_for_overridden(
    typ: Type[Any],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs,
) -> Tuple[Any, MemoType, ForwardRefs]:
    rv = None
    if typ in overrides:
        override: schema.TypeExtension = overrides[typ]
        schema_type_type, schema_node_children = override.schema
        type_schema = schema.nodes.SchemaNode(schema_type_type())
        for child in schema_node_children:
            type_schema.add(child)
        rv = type_schema
    return rv, memo, forward_refs


PARSING_ORDER = pvector([ _maybe_node_for_forward_ref
                        , _maybe_node_for_overridden
                        , _maybe_node_for_none
                        , _maybe_node_for_primitive
                        , _maybe_node_for_type_var
                        , _maybe_node_for_newtype
                        , _maybe_node_for_union
                        , _maybe_node_for_sequence
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


CompoundSchema = Union[schema.nodes.SchemaNode, schema.nodes.TupleSchema, schema.nodes.SequenceSchema]


def decide_node_type(
    typ: Type[iface.IType],
    overrides: OverridesT,
    memo: MemoType,
    forward_refs: ForwardRefs,
) -> Tuple[CompoundSchema, MemoType, ForwardRefs]:
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
        return memo[typ], memo, forward_refs
    for attempt_find in PARSING_ORDER:
        node, memo, forward_refs = attempt_find(typ, overrides, memo, forward_refs)
        if node:
            memo = memo.set(typ, node)
            return node, memo, forward_refs
    raise TypeError(
        f'Unable to create a node for "{typ}".'
    )
