import enum as std_enum
import typing as t
import pathlib

import typing_inspect as insp
import colander as col
from pyrsistent import pmap, pvector
from pyrsistent.typing import PMap

from .errors import Invalid
from .. import sums
from .. import interface as iface
from . import primitives
from . import meta
from . import nodes


Null = nodes.Null


class TypedMapping(meta.Mapping):
    def __init__(self, *, key_node: nodes.SchemaNode, value_node: nodes.SchemaNode):
        # https://docs.pylonsproject.org/projects/colander/en/latest/api.html#colander.Mapping
        super().__init__(unknown='preserve')
        self.key_node = key_node
        self.value_node = value_node

    def deserialize(self, node, cstruct):
        r = super().deserialize(node, cstruct)
        if r in (Null, None):
            return r
        rv = {}
        for k, v in r.items():
            try:
                key = self.key_node.deserialize(k)
            except Invalid as e:
                error = Invalid(node, "{<k>: <v>} error parsing <k>", cstruct)
                error.add(e)
                raise error
            else:
                try:
                    val = self.value_node.deserialize(v)
                except Invalid as e:
                    error = Invalid(node, f"{{{k}: <v>}} error parsing <v>", v)
                    error.add(e)
                    raise error
                else:
                    rv[key] = val
        return {self.key_node.deserialize(k): self.value_node.deserialize(v) for k, v in r.items()}

    def serialize(self, node, appstruct):
        r = super().serialize(node, appstruct)
        if r in (Null, None):
            return r

        return {self.key_node.serialize(k): self.value_node.serialize(v) for k, v in r.items()}


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


class Structure(meta.Mapping):
    """ SchemaNode for NamedTuples and derived types.
    """
    def __init__(self,
                 typ: t.Type[iface.IType],
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
        return f'Structure({self.typ})'

    def deserialize(self, node, cstruct):
        r = super().deserialize(node, cstruct)
        if r is Null:
            return r
        return self.typ(**{
            self.deserialize_overrides.get(k, k): v
            for k, v in r.items()
        })

    def serialize(self, node, appstruct: iface.IType) -> t.Mapping[str, t.Any]:
        if appstruct is Null:
            return super().serialize(node, appstruct)
        return super().serialize(
            node,
            {
                self.serialize_overrides.get(attr_name, attr_name): getattr(appstruct, attr_name)
                for attr_name in self.attrs
            }
        )


Tuple = meta.Tuple


class Sum(meta.SchemaType):
    def __init__(
        self,
        typ: sums.SumType,
        variant_nodes: t.Sequence[
            t.Tuple[
                t.Type, t.Union[nodes.SchemaNode, col.SequenceSchema, col.TupleSchema]
            ],
        ],
        as_dict_key: t.Optional[str] = None,
    ) -> None:
        super().__init__()
        self.typ = typ
        self.variant_nodes = variant_nodes
        self.as_dict_key = as_dict_key
        self.variant_schema_types: t.Set[meta.SchemaType] = {
            x.typ for _, x in variant_nodes
        }

    def deserialize(self, node, cstruct):
        if cstruct in (Null, None):
            # explicitly passed None is not col.null
            # therefore we must handle both
            return cstruct

        if self.as_dict_key:
            try:
                tag = cstruct[self.as_dict_key]
            except (KeyError, ValueError) as e:
                raise Invalid(
                    node,
                    f'Incorrect data layout for this type: '
                    f'tag is not present as key "{self.as_dict_key}"',
                    cstruct
                ) from e
            try:
                payload = {k: v for k, v in cstruct.items() if k != self.as_dict_key}
            except (AttributeError, TypeError) as e:
                raise Invalid(
                    node,
                    'Incorrect data layout for this type: payload is not a mapping',
                    cstruct
                ) from e
        else:
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
            except Invalid as e:
                raise Invalid(
                    node,
                    f'Incorrect payload format for '
                    f'{var_type.__variant_meta__.variant_of.__name__}.{var_type.__variant_meta__.variant_name}',
                    cstruct
                )
            return var_type(**variant_struct._asdict())

        raise Invalid(
            node,
            'None of the expected variants matches provided data',
            cstruct
        )

    def serialize(self, node, appstruct: t.Any):
        if appstruct in (Null, None):
            return None

        for var_type, var_schema in self.variant_nodes:
            if isinstance(appstruct, var_type):
                if self.as_dict_key:
                    rv = var_schema.serialize(appstruct)
                    rv[self.as_dict_key] = var_type.__variant_meta__.value
                    return rv
                else:
                    return (var_type.__variant_meta__.value, var_schema.serialize(appstruct))

        raise Invalid(
            node,
            'None of the expected variants matches provided structure',
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
            raise Invalid(node, f'Invalid variant of {self.typ.__name__}: {cstruct}', cstruct)


generic_type_bases: t.Callable[[t.Type], t.Tuple[t.Type, ...]] = lambda x: (insp.get_origin(x),)


class Literal(meta.SchemaType):
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
            'None of the Literal variants matches provided data',
            cstruct
        )

    def serialize(self, node, appstruct: t.Any):
        if appstruct is Null:
            return None
        if appstruct in self.variants:
            return appstruct
        raise Invalid(
            node,
            'None of the Literal variants matches provided data',
            appstruct
        )


class Union(meta.SchemaType):
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
        self.variant_schema_types: t.Set[meta.SchemaType] = {
            x.typ for _, x in variant_nodes
        }

    def __repr__(self) -> str:
        return f'Optional({self.variant_schema_types})' if len(self.variant_schema_types) == 1 else f'Union({self.variant_schema_types})'

    def deserialize(self, node, cstruct):
        if cstruct in (Null, None):
            # explicitly passed None is not col.null
            # therefore we must handle both
            return cstruct

        collected_errors: t.List[Invalid] = []
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
            except Invalid as e:
                collected_errors.append(e)

        # next, iterate over available variants and return the first
        # matched structure.
        remaining_variants = (
            x for _, x in self.variant_nodes
            if x.typ is not prim_schema_type
        )
        for variant in remaining_variants:
            try:
                return variant.deserialize(cstruct)
            except Invalid as e:
                collected_errors.append(e)
                continue

        errors = "\n\t * ".join(str(x.node) for x in collected_errors)
        error = Invalid(
            node,
            f'No suitable variant among tried:\n\t * {errors}\n',
            cstruct
        )
        for e in collected_errors:
            error.add(e)
        raise error

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

        collected_errors = []
        for var_type, var_schema in remaining_variants:
            # Mappings (which are not structs) have their own serializer
            if isinstance(var_schema.typ, TypedMapping) and not isinstance(var_schema, Structure):
                try:
                    return var_schema.serialize(appstruct)
                except Invalid as e:
                    collected_errors.append(e)
                    continue

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
                except Invalid as e:
                    collected_errors.append(e)
                    continue

            elif isinstance(var_schema, col.TupleSchema):
                if not isinstance(appstruct, tuple):
                    continue
                try:
                    return var_schema.serialize(appstruct)
                except Invalid as e:
                    collected_errors.append(e)
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
                if struct_type in matching_types or isinstance(var_type, t.ForwardRef) or issubclass(struct_type, var_type):
                    try:
                        return var_schema.serialize(appstruct)
                    except Invalid as e:
                        collected_errors.append(e)

        raise Invalid(
            node,
            f'None of the expected variants matches provided structure. Matched and tried: {collected_errors}',
            appstruct
        )


class ForwardReferenceType(meta.SchemaType):
    """ A special type that is promised to understand how to serialise and serialise a given
    reference of a type that will be resolved at a later stage of parsing
    """
    def __init__(self, forward_ref: t.ForwardRef, ref_registry):
        super().__init__()
        self.ref = forward_ref
        self.ref_registry = ref_registry

    def __repr__(self) -> str:
        return f'ForwardReferenceType(typ={self.ref})'

    def deserialize(self, node, cstruct):
        rv = self.ref_registry[self.ref].deserialize(cstruct)
        return rv

    def serialize(self, node, appstruct):
        rv = self.ref_registry[self.ref].serialize(appstruct)
        return rv


SUBCLASS_BASED_TO_SCHEMA_TYPE: t.Mapping[
    t.Tuple[t.Type, ...], t.Type[meta.SchemaType],
] = {
    (std_enum.Enum,): Enum,
    # Pathlib's PurePath and its derivatives
    (pathlib.PurePath,): Path,
}
