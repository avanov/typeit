from typing import (
    Type, Tuple, Optional, Any, Union, List, Set,
    Dict, Callable,
    Sequence, get_type_hints,
    MutableSet, TypeVar, FrozenSet, Mapping,
)
from typing_extensions import Literal
import collections

import colander as col
import typing_inspect as insp
from pyrsistent import pmap, pvector
from pyrsistent import typing as pyt

from .definitions import OverridesT, NO_OVERRIDES
from .utils import is_named_tuple
from . import compat
from . import flags
from . import schema
from . import sums
from .schema.meta import TypeExtension
from . import interface as iface


T = TypeVar('T')

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


def _maybe_node_for_primitive(
    typ: Union[Type[iface.IType], Any],
    overrides: OverridesT
) -> Optional[schema.nodes.SchemaNode]:
    """ Check if type could be associated with one of the
    built-in type converters (in terms of Python built-ins).
    """
    if flags.NON_STRICT_PRIMITIVES in overrides:
        registry = schema.primitives.NON_STRICT_BUILTIN_TO_SCHEMA_TYPE
    else:
        registry = schema.primitives.BUILTIN_TO_SCHEMA_TYPE

    try:
        schema_type = registry[typ]
    except KeyError:
        return None

    return schema.nodes.SchemaNode(schema_type)


def _maybe_node_for_type_var(
    typ: Type,
    overrides: OverridesT
) -> Optional[schema.nodes.SchemaNode]:
    """ When we parse Sequence and List definitions without
    clarified item type, it is possible that this item is defined
    as TypeVar. Since it's an indicator of a generic collection,
    we can treat it as typing.Any.
    """
    if isinstance(typ, TypeVar):
        return _maybe_node_for_primitive(Any, overrides)
    return None


def _maybe_node_for_subclass_based(
    typ: Type[iface.IType],
    overrides: OverridesT
) -> Optional[schema.nodes.SchemaNode]:
    for subclasses, schema_typ in schema.types.SUBCLASS_BASED_TO_SCHEMA_TYPE.items():
        try:
            is_target = issubclass(typ, subclasses)
        except TypeError:
            # TypeError: issubclass() arg 1 must be a class
            # ``typ`` is not a class, skip the rest
            return None
        else:
            if is_target:
                return schema.nodes.SchemaNode(schema_typ(typ, allow_empty=True))
    return None


def _maybe_node_for_union(
    typ: Type[iface.IType],
    overrides: OverridesT,
    supported_type=frozenset({}),
    supported_origin=frozenset({
        Union,
    })
) -> Optional[schema.nodes.SchemaNode]:
    """ Handles cases where typ is a Union, including the special
    case of Optional[Any], which is in essence Union[None, T]
    where T is either unknown Any or a concrete type.
    """
    if typ in supported_type or insp.get_origin(typ) in supported_origin:
        NoneClass = None.__class__
        variants = inner_type_boundaries(typ)
        if variants in ((NoneClass, Any), (Any, NoneClass)):
            # Case for Optional[Any] and Union[None, Any] notations
            return schema.nodes.SchemaNode(
                schema.primitives.AcceptEverything(),
                missing=None
            )

        allow_empty = NoneClass in variants
        # represents a 2-tuple of (type_from_signature, associated_schema_node)
        variant_nodes: List[Tuple[Type, schema.nodes.SchemaNode]] = []
        for variant in variants:
            if variant is NoneClass:
                continue
            node = decide_node_type(variant, overrides)
            if allow_empty:
                node.missing = None
            variant_nodes.append((variant, node))

        if flags.NON_STRICT_PRIMITIVES in overrides:
            primitive_types = schema.primitives.NON_STRICT_BUILTIN_TO_SCHEMA_TYPE
        else:
            primitive_types = schema.primitives.BUILTIN_TO_SCHEMA_TYPE

        union_node = schema.nodes.SchemaNode(
            schema.types.Union(variant_nodes=variant_nodes,
                               primitive_types=primitive_types)
        )
        if allow_empty:
            union_node.missing = None
        return union_node

    return None


def _maybe_node_for_sum_type(
    typ: Type[iface.IType],
    overrides: OverridesT,
    supported_type=frozenset({}),
    supported_origin=frozenset({})
) -> Optional[schema.nodes.SchemaNode]:
    if issubclass(typ, sums.SumType):
        # represents a 2-tuple of (type_from_signature, associated_schema_node)
        variant_nodes: List[Tuple[Type, schema.nodes.SchemaNode]] = []
        for variant in typ:
            node = decide_node_type(variant.__variant_meta__.constructor, overrides)
            variant_nodes.append((variant, node))
        sum_node = schema.nodes.SchemaNode(
            schema.types.Sum(typ=typ, variant_nodes=variant_nodes)
        )
        return sum_node
    return None


def _maybe_node_for_literal(
    typ: Type[iface.IType],
    overrides: OverridesT,
    supported_type=frozenset({}),
    supported_origin=frozenset({
        Literal,
        insp.get_generic_type(Literal)  # py3.6 fix
    }),
    _supported_literal_types=frozenset({
        bool, int, str, bytes, NoneType,
    })
) -> Optional[schema.nodes.SchemaNode]:
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
        return schema.nodes.SchemaNode(schema.types.Literal(frozenset(inner)))
    return None


def _maybe_node_for_list(
    typ: Type[iface.IType],
    overrides: OverridesT,
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
) -> Optional[col.SequenceSchema]:
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
        return seq_type(decide_node_type(inner, overrides))
    return None


def _maybe_node_for_set(
    typ: Type[iface.IType],
    overrides: OverridesT,
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
        return schema.nodes.SetSchema(
            decide_node_type(inner, overrides),
            frozen=(
                typ is frozenset or
                origin in (frozenset, FrozenSet)
            )
        )
    return None


def _maybe_node_for_tuple(
    typ: Type[iface.IType],
    overrides: OverridesT,
    supported_type=frozenset({
        tuple,
    }),
    supported_origin=frozenset({
        tuple, Tuple,
    })
) -> Optional[col.TupleSchema]:
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
        inner_nodes = (decide_node_type(t, overrides) for t in inner_types)
        for n in inner_nodes:
            node.add(n)
        return node
    return None


def _maybe_node_for_dict(
    typ: Type[iface.IType],
    overrides: OverridesT,
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
) -> Optional[schema.nodes.SchemaNode]:
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
        return map_type()
    return None


def _node_for_type(
    typ: Type[iface.IType],
    overrides: OverridesT
) -> Optional[schema.nodes.SchemaNode]:
    """ Generates a Colander schema for the given `typ` that is capable
    of both constructing (deserializing) and serializing the `typ`.
    """
    if type(typ) is not type:
        return None

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

        node_type = decide_node_type(field_type, overrides)
        if node_type is None:
            raise TypeError(
                f'Cannot recognise type "{field_type}" of the field '
                f'"{typ.__name__}.{field_name}" (from {typ.__module__})'
            )
        node_type.name = serialized_field_name
        type_schema.add(node_type)
    return type_schema


def _maybe_node_for_overridden(
    typ: Type[Any],
    overrides: OverridesT
):
    if typ in overrides:
        override: schema.TypeExtension = overrides[typ]
        return override.schema
    return None


PARSING_ORDER = [ _maybe_node_for_overridden
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
                , _node_for_type ]


def decide_node_type(
    typ: Type[iface.IType],
    overrides: OverridesT
) -> Union[schema.nodes.SchemaNode, col.TupleSchema, col.SequenceSchema]:
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
    for step in PARSING_ORDER:
        node = step(typ, overrides)
        if node:
            return node
    raise TypeError(
        f'Unable to create a node for "{typ}".'
    )


TypeTools = Tuple[ Callable[[Dict[str, Any]], T]
                 , Callable[[T], Union[List, Dict]] ]


class _TypeConstructor:
    def __init__(self, overrides: Union[Dict, OverridesT] = NO_OVERRIDES):
        self.overrides = pmap(overrides)

    def __call__(self,
        typ: Type[T],
        overrides: OverridesT = NO_OVERRIDES
    ) -> TypeTools:
        """ Generate a constructor and a serializer for the given type

        :param overrides: a mapping of type_field => serialized_field_name.
        """
        schema_node = _node_for_type(typ, overrides)
        if not schema_node:
            raise TypeError(
                f'Cannot create a type constructor for {typ}'
            )
        return schema_node.deserialize, schema_node.serialize

    def __and__(self, override: OverrideT) -> '_TypeConstructor':
        if isinstance(override, flags._Flag):
            overrides = self.overrides.set(override, True)
        elif isinstance(override, schema.meta.TypeExtension):
            overrides = self.overrides.set(override.typ, override)
        else:
            overrides = self.overrides.update(override)
        return self.__class__(overrides=overrides)

    def __xor__(self, typ: Type[T]) -> TypeTools:
        return self.__call__(typ, self.overrides)


type_constructor = _TypeConstructor()
