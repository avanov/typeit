import enum as std_enum
import pathlib
from typing import Type, Sequence, Union, Any, Mapping, Tuple, Set, Callable
import typing_inspect as insp

import colander as col

from ..definitions import OverridesT
from ..sums import SumType
from .. import interface as iface
from ..compat import PY_VERSION

from . import primitives


generic_type_bases: Callable[[Type], Tuple[Type, ...]] = (
    insp.get_generic_bases if PY_VERSION < (3, 7) else
    lambda x: (insp.get_origin(x),)
)


EnumLike = Union[std_enum.Enum, SumType]


class Enum(col.Str):
    def __init__(self, typ: Type[EnumLike], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.typ = typ

    def serialize(self, node, appstruct):
        if appstruct is col.null:
            return appstruct
        r = super().serialize(node, appstruct.value)
        return r

    def deserialize(self, node, cstruct) -> std_enum.Enum:
        r = super().deserialize(node, cstruct)
        if r is col.null:
            return r
        try:
            return self.typ(r)
        except ValueError:
            raise col.Invalid(node, f'Invalid variant of {self.typ.__name__}', cstruct)


class Path(col.Str):
    def __init__(self, typ: Type[pathlib.PurePath], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.typ = typ

    def serialize(self, node, appstruct: Union[col._null, pathlib.PurePath]):
        if appstruct is col.null:
            return appstruct
        r = super().serialize(node, str(appstruct))
        return r

    def deserialize(self, node, cstruct) -> pathlib.PurePath:
        r = super().deserialize(node, cstruct)
        if r is col.null:
            return r
        try:
            return self.typ(r)
        except TypeError:
            raise col.Invalid(node, f'Invalid variant of {self.typ.__name__}', cstruct)


class Structure(col.Mapping):
    """ SchemaNode for NamedTuples and derived types.
    """
    def __init__(self,
                 typ: Type[iface.IType],
                 overrides: OverridesT,
                 unknown: str = 'ignore') -> None:
        super().__init__(unknown)
        self.typ = typ
        # source_field_name => struct_field_name
        self.deserialize_overrides = {
            overrides[getattr(typ, x)]: x
            for x in typ._fields
            if getattr(typ, x) in overrides
        }
        # struct_field_name => source_field_name
        self.serialize_overrides = {
            v: k for k, v in self.deserialize_overrides.items()
        }

    def __repr__(self) -> str:
        return f'Structure(typ={self.typ})'

    def deserialize(self, node, cstruct):
        r = super().deserialize(node, cstruct)
        if r is col.null:
            return r
        return self.typ(**{
            self.deserialize_overrides.get(k, k): v
            for k, v in r.items()
        })

    def serialize(self, node, appstruct: iface.IType):
        if appstruct is col.null:
            return super().serialize(node, appstruct)
        return super().serialize(
            node,
            {
                self.serialize_overrides.get(k, k): v
                for k, v in appstruct._asdict().items()
            }
        )


class UnionNode(col.SchemaType):
    """ This node handles Union[T1, T2, ...] cases.
    Please note that Optional[T] is normalized by parser as Union[None, T],
    and this UnionNode will not have None among its variants. Instead,
    `UnionNode.missing` will be set to None, indicating the value for missing
    data.
    """
    def __init__(
        self,
        variant_nodes: Sequence[
            Tuple[
                Type, Union[col.SchemaNode, col.SequenceSchema, col.TupleSchema]
            ],
        ],
        primitive_types: Union[
            Mapping[Type, primitives.PrimitiveSchemaTypeT],
            Mapping[Type, primitives.NonStrictPrimitiveSchemaTypeT],
        ]
    ) -> None:
        super().__init__()
        self.primitive_types = primitive_types
        self.variant_nodes = variant_nodes
        self.variant_schema_types: Set[col.SchemaType] = {
            x.typ for _, x in variant_nodes
        }

    def deserialize(self, node, cstruct):
        if cstruct is None:
            # explicitly passed None is not col.null
            # therefore we must handle it separately
            return cstruct

        if cstruct is col.null:
            return cstruct

        # Firstly, let's see if `cstruct` is one of the primitive types
        # supported by Python, and if this primitive type is specified
        # among union variants. If it is, then we need to try
        # a constructor of that primitive type first.
        # We do it to support cases like `Union[str, int, float]`,
        # where a value of 1.0 should be handled as float despite the
        # fact that both str() and int() constructors can happily
        # handle that value and return one of the expected variants
        # (but incorrectly!)
        prim_schema_type = self.primitive_types.get(type(cstruct))
        if prim_schema_type in self.variant_schema_types:
            try:
                return prim_schema_type.deserialize(node, cstruct)
            except col.Invalid:
                pass

        # next, iterate over available variants and return the first
        # matched structure.
        remaining_variants = (
            x for _, x in self.variant_nodes
            if x.typ is not prim_schema_type
        )
        for variant in remaining_variants:
            try:
                return variant.deserialize(cstruct)
            except col.Invalid:
                continue

        raise col.Invalid(
            node,
            'None of the variants matches provided data. ',
            cstruct
        )

    def serialize(self, node, appstruct: Any):
        if appstruct in (col.null, None):
            return None

        struct_type = type(appstruct)

        prim_schema_type = self.primitive_types.get(struct_type)
        if prim_schema_type in self.variant_schema_types:
            try:
                return prim_schema_type.serialize(node, appstruct)
            except col.Invalid:
                pass

        remaining_variants = (
            (t, s)
            for (t, s) in self.variant_nodes
            if s.typ is not prim_schema_type
        )

        for var_type, var_schema in remaining_variants:
            # Sequences and tuples require special treatment here:
            # since there is no direct reference to the target python data type
            # through variant.typ.typ that we could use to compare this variant
            # with appstruct's type, we just check if the appstruct is a list-like
            # object. And if it is, we apply SequenceSchema's serializer on it,
            # otherwise we skip this variant (we need to do that to make sure that
            # a Union variant matches appstruct's type as close as possible)
            # if isinstance(struct_type, (list, tuple, set))
            if isinstance(var_schema, col.SequenceSchema):
                if not isinstance(appstruct, list):
                    continue
                try:
                    return var_schema.serialize(appstruct)
                except col.Invalid:
                    continue

            elif isinstance(var_schema, col.TupleSchema):
                if not isinstance(appstruct, tuple):
                    continue
                try:
                    return var_schema.serialize(appstruct)
                except col.Invalid:
                    continue

            else:
                # schema.SchemaNode
                # We need to check if the type of the appstruct
                # is the same as the type that appears in the Union
                # definition and is associated with this SchemaNode.
                # get_origin() normalizes meta-types like `typing.Dict`
                # to dict class etc.
                #  Please note that the order of checks matters here, since
                # subscripted generics like typing.Dict cannot be used with
                # issubclass
                if insp.is_generic_type(var_type):
                    matching_types = (var_type,) + generic_type_bases(var_type)
                else:
                    matching_types = (insp.get_origin(var_type), var_type)
                if struct_type in matching_types or issubclass(struct_type, var_type):
                    return var_schema.serialize(appstruct)

        raise col.Invalid(
            node,
            'None of the variants matches provided structure. ',
            appstruct
        )


class SetSchema(col.SequenceSchema):
    def __init__(self, *args, frozen=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.frozen = frozen

    def deserialize(self, *args, **kwargs):
        r = super().deserialize(*args, **kwargs)
        if r in (col.null, None):
            return r
        if self.frozen:
            return frozenset(r)
        return set(r)


class SchemaNode(col.SchemaNode):
    """ Colander's SchemaNode doesn't show node type in it's repr,
    we fix it with this subclass.
    """
    def __repr__(self) -> str:
        return f'SchemaNode({self.typ})'


# Maps primitive types that appear in type signatures
# to colander SchemaNodes responsible for serialization/deserialization
BUILTIN_TO_SCHEMA_TYPE: Mapping[Type, primitives.PrimitiveSchemaTypeT] = {
    Any: primitives.AcceptEverything(),
    str: primitives.Str(allow_empty=True),
    int: primitives.Int(),
    float: primitives.Float(),
    bool: primitives.Bool(),
}


NON_STRICT_BUILTIN_TO_SCHEMA_TYPE: Mapping[Type, primitives.NonStrictPrimitiveSchemaTypeT] = {
    Any: primitives.AcceptEverything(),
    str: primitives.NonStrictStr(allow_empty=True),
    int: primitives.NonStrictInt(),
    float: primitives.NonStrictFloat(),
    bool: primitives.NonStrictBool(),
}


_SUBCLASS_BASED_TO_SCHEMA_NODE: Mapping[
    Tuple[Type, ...], Type[col.SchemaNode],
] = {
    (std_enum.Enum, SumType): Enum,
    # Pathlib's PurePath and its derivatives
    (pathlib.PurePath,): Path,
}
