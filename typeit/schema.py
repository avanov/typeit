import enum as std_enum
from typing import Type, Tuple, NamedTuple, Sequence, Union

import colander as col

from .sums import SumType
from .utils import normalize_name, denormalize_name


EnumLike = Union[std_enum.Enum, SumType]


class Enum(col.Str):
    def __init__(self, enum: Type[EnumLike], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.enum = enum

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
            return self.enum(r)
        except ValueError:
            raise col.Invalid(node, f'Invalid variant of {self.enum.__name__}', cstruct)


class Structure(col.Mapping):

    def __init__(self,
                 typ: Type[Tuple],
                 unknown: str = 'ignore') -> None:
        super().__init__(unknown)
        self.typ = typ

    def __repr__(self):
        return f'Structure(typ={self.typ})'

    def deserialize(self, node, cstruct):
        r = super().deserialize(node, cstruct)
        if r is col.null:
            return r
        return self.typ(**{normalize_name(k)[0]: v for k, v in r.items()})

    def serialize(self, node, appstruct: NamedTuple):
        if appstruct is col.null:
            return super().serialize(node, appstruct)
        return super().serialize(
            node,
            {denormalize_name(k)[0]: v for k, v in appstruct._asdict().items()}
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

        for variant in self.variants:
            try:
                return variant.serialize(appstruct)
            except col.Invalid:
                continue


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


BUILTIN_TO_SCHEMA_TYPE = {
    str: Str(allow_empty=True),
    int: Int(),
    float: col.Float(),
    bool: Bool(),
}
