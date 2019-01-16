import enum as std_enum
from typing import Type, NamedTuple, Sequence, Union, Any

import colander as col

from .definitions import OverridesT
from .sums import SumType


EnumLike = Union[std_enum.Enum, SumType]


class AcceptEverything(col.SchemaType):
    """ A schema type to correspond to typing.Any, i.e. allows
    any data to pass through the type constructor.
    """
    def serialize(self, node, appstruct):
        return appstruct

    def deserialize(self, node, cstruct):
        return cstruct


class Enum(col.Str):
    def __init__(self, typ: Type[EnumLike], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.typ = typ

    def serialize(self, node, appstruct):
        """ Default colander integer serializer returns a string representation
        of a number, whereas we want identical representation of the original data.
        """
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


class Structure(col.Mapping):

    def __init__(self,
                 typ: Type[NamedTuple],
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

    def serialize(self, node, appstruct: NamedTuple):
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
    def __init__(self,
                 variants: Sequence[col.SchemaNode]) -> None:
        super().__init__()
        self.variants = variants
        self.variant_types = {x.typ for x in variants}

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
        prim_schema_type = BUILTIN_TO_SCHEMA_TYPE.get(type(cstruct))
        if prim_schema_type in self.variant_types:
            try:
                return prim_schema_type.deserialize(node, cstruct)
            except col.Invalid:
                pass

        # next, iterate over available variants and return the first
        # matched structure.
        remaining_variants = (
            x for x in self.variants
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

    def serialize(self, node, appstruct: NamedTuple):
        if appstruct in (col.null, None):
            return None

        struct_type = type(appstruct)

        prim_schema_type = BUILTIN_TO_SCHEMA_TYPE.get(struct_type)
        if prim_schema_type in self.variant_types:
            try:
                return prim_schema_type.serialize(node, appstruct)
            except col.Invalid:
                pass

        remaining_variants = (
            x for x in self.variants
            if x.typ is not prim_schema_type
        )

        for variant in remaining_variants:
            if variant.typ.typ is not struct_type:
                continue
            return variant.serialize(appstruct)


class Int(col.Int):

    def serialize(self, node, appstruct):
        """ Default colander integer serializer returns a string representation
        of a number, whereas we want identical representation of the original data.
        """
        r = super().serialize(node, appstruct)
        if r is col.null:
            return r
        return int(r)


class Bool(col.Bool):

    def serialize(self, node, appstruct):
        """ Default colander bool serializer returns a string representation
        of a boolean flag, whereas we want identical representation of the original data.
        """
        r = super().serialize(node, appstruct)
        if r is col.null:
            return r
        return {'false': False, 'true': True}[r]


class Str(col.Str):

    def serialize(self, node, appstruct):
        """ Default colander str serializer serializes None as 'None',
        whereas we want identical representation of the original data.
        """
        r = super().serialize(node, appstruct)
        if r in (col.null, 'None'):
            return None
        return r


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


BUILTIN_TO_SCHEMA_TYPE = {
    Any: AcceptEverything(),
    str: Str(allow_empty=True),
    int: Int(),
    float: col.Float(),
    bool: Bool(),
}
