import enum as std_enum
import typing as t
import pathlib

import typing_inspect as insp
import colander as col
from pyrsistent import pmap, pvector
from pyrsistent.typing import PMap

from .errors import Invalid
from .. import sums
from ..definitions import OverridesT
from .. import interface as iface
from ..compat import PY_VERSION
from . import primitives
from . import meta
from . import nodes


SchemaType = col.SchemaType
Null = nodes.Null


class Path(primitives.Str):
    def __init__(self, typ: t.Type[pathlib.PurePath], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.typ = typ

    def serialize(self, node, appstruct: t.Union[col._null, pathlib.PurePath]):
        if appstruct is Null:
            return appstruct
        r = super().serialize(node, str(appstruct))
        return r

    def deserialize(self, node, cstruct) -> pathlib.PurePath:
        r = super().deserialize(node, cstruct)
        if r is Null:
            return r
        try:
            return self.typ(r)
        except TypeError:
            raise Invalid(node, f'Invalid variant of {self.typ.__name__}', cstruct)


class Structure(col.Mapping):
    """ SchemaNode for NamedTuples and derived types.
    """
    def __init__(self,
                 typ: t.Type[iface.IType],
                 overrides: OverridesT,
                 attrs: t.Sequence[str] = pvector([]),
                 deserialize_overrides: PMap[str, str] = pmap({}),
                 unknown: str = 'ignore',
                 ) -> None:
        """
        :param deserialize_overrides: source_field_name => struct_field_name mapping
        """
        super().__init__(unknown)
        self.typ = typ
        self.attrs = attrs
        self.deserialize_overrides = deserialize_overrides
        # struct_field_name => source_field_name
        self.serialize_overrides = pmap({
            v: k for k, v in self.deserialize_overrides.items()
        })

    def __repr__(self) -> str:
        return f'Structure(typ={self.typ})'

    def deserialize(self, node, cstruct):
        r = super().deserialize(node, cstruct)
        if r is Null:
            return r
        return self.typ(**{
            self.deserialize_overrides.get(k, k): v
            for k, v in r.items()
        })

    def serialize(self, node, appstruct: iface.IType):
        if appstruct is Null:
            return super().serialize(node, appstruct)
        return super().serialize(
            node,
            {
                self.serialize_overrides.get(attr_name, attr_name): getattr(appstruct, attr_name)
                for attr_name in self.attrs
            }
        )


class Tuple(col.Tuple, metaclass=meta.SubscriptableSchemaTypeM):
    pass


class Sum(SchemaType, metaclass=meta.SubscriptableSchemaTypeM):
    def __init__(
        self,
        typ: sums.SumType,
        variant_nodes: t.Sequence[
            t.Tuple[
                t.Type, t.Union[nodes.SchemaNode, col.SequenceSchema, col.TupleSchema]
            ],
        ],
    ) -> None:
        super().__init__()
        self.typ = typ
        self.variant_nodes = variant_nodes
        self.variant_schema_types: t.Set[col.SchemaType] = {
            x.typ for _, x in variant_nodes
        }

    def deserialize(self, node, cstruct):
        if cstruct in (Null, None):
            # explicitly passed None is not col.null
            # therefore we must handle both
            return cstruct

        try:
            tag, payload = cstruct
        except ValueError:
            raise Invalid(
                node,
                'Incorrect data layout for this type.',
                cstruct
            )
        # next, iterate over available variants and return the first
        # matched structure.
        for var_type, var_schema in self.variant_nodes:
            if var_type.__variant_meta__.value != tag:
                continue
            try:
                variant_struct = var_schema.deserialize(payload)
            except Invalid:
                raise Invalid(
                    node,
                    'Incorrect payload format.',
                    cstruct
                )
            return var_type(**variant_struct._asdict())

        raise Invalid(
            node,
            'None of the variants matches provided data.',
            cstruct
        )

    def serialize(self, node, appstruct: t.Any):
        if appstruct in (Null, None):
            return None

        for var_type, var_schema in self.variant_nodes:
            if isinstance(appstruct, var_type):
                return (var_type.__variant_meta__.value, var_schema.serialize(appstruct))

        raise Invalid(
            node,
            'None of the variants matches provided structure.',
            appstruct
        )


EnumLike = std_enum.Enum


class Enum(primitives.Str):
    def __init__(self, typ: t.Type[EnumLike], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.typ = typ

    def serialize(self, node, appstruct):
        if appstruct is Null:
            return appstruct
        r = super().serialize(node, appstruct.value)
        return r

    def deserialize(self, node, cstruct) -> std_enum.Enum:
        r = super().deserialize(node, cstruct)
        if r is Null:
            return r
        try:
            return self.typ(r)
        except ValueError:
            raise Invalid(node, f'Invalid variant of {self.typ.__name__}', cstruct)





generic_type_bases: t.Callable[[t.Type], t.Tuple[t.Type, ...]] = (
    insp.get_generic_bases if PY_VERSION < (3, 7) else
    lambda x: (insp.get_origin(x),)
)


class Literal(SchemaType, metaclass=meta.SubscriptableSchemaTypeM):
    def __init__(self, variants: t.FrozenSet):
        super().__init__()
        self.variants = variants

    def deserialize(self, node, cstruct):
        if cstruct is Null:
            # explicitly passed None is not col.null
            # therefore we must handle it separately
            return cstruct
        if cstruct in self.variants:
            return cstruct
        raise Invalid(
            node,
            'None of the Literal variants matches provided data.',
            cstruct
        )

    def serialize(self, node, appstruct: t.Any):
        if appstruct is Null:
            return None
        if appstruct in self.variants:
            return appstruct
        raise Invalid(
            node,
            'None of the Literal variants matches provided data.',
            appstruct
        )


class Union(SchemaType, metaclass=meta.SubscriptableSchemaTypeM):
    """ This node handles typing.Union[T1, T2, ...] cases.
    Please note that typing.Optional[T] is normalized by parser as typing.Union[None, T],
    and this Union schema type will not have None among its variants. Instead,
    `Union.missing` will be set to None, indicating the value for missing
    data.
    """
    def __init__(
        self,
        variant_nodes: t.Sequence[
            t.Tuple[
                t.Type,t.Union[nodes.SchemaNode, col.SequenceSchema, col.TupleSchema]
            ],
        ],
        primitive_types: t.Union[
            t.Mapping[t.Type, primitives.PrimitiveSchemaTypeT],
            t.Mapping[t.Type, primitives.NonStrictPrimitiveSchemaTypeT],
        ]
    ) -> None:
        super().__init__()
        self.primitive_types = primitive_types
        self.variant_nodes = variant_nodes
        self.variant_schema_types: t.Set[col.SchemaType] = {
            x.typ for _, x in variant_nodes
        }

    def deserialize(self, node, cstruct):
        if cstruct in (Null, None):
            # explicitly passed None is not col.null
            # therefore we must handle both
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
            except Invalid:
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
            except Invalid:
                continue

        raise Invalid(
            node,
            'None of the variants matches provided data.',
            cstruct
        )

    def serialize(self, node, appstruct: t.Any):
        if appstruct in (Null, None):
            return None

        struct_type = type(appstruct)

        prim_schema_type = self.primitive_types.get(struct_type)
        if prim_schema_type in self.variant_schema_types:
            try:
                return prim_schema_type.serialize(node, appstruct)
            except Invalid:
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
                except Invalid:
                    continue

            elif isinstance(var_schema, col.TupleSchema):
                if not isinstance(appstruct, tuple):
                    continue
                try:
                    return var_schema.serialize(appstruct)
                except Invalid:
                    continue

            else:
                # nodes.SchemaNode
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

        raise Invalid(
            node,
            'None of the variants matches provided structure.',
            appstruct
        )


SUBCLASS_BASED_TO_SCHEMA_TYPE: t.Mapping[
    t.Tuple[t.Type, ...], t.Type[SchemaType],
] = {
    (std_enum.Enum,): Enum,
    # Pathlib's PurePath and its derivatives
    (pathlib.PurePath,): Path,
}
