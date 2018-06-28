import enum as std_enum
from typing import Type, Tuple, NamedTuple, Sequence

import colander as col

from .utils import normalize_name, denormalize_name


class Enum(col.Str):
    def __init__(self, enum: Type[std_enum.Enum], *args, **kwargs) -> None:
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


class UnionNode(col.Mapping):
    def __init__(self,
                 variants: Sequence[col.SchemaNode]) -> None:
        super().__init__(unknown='preserve')
        self.variants = variants

    def deserialize(self, node, cstruct):
        if cstruct is None:
            # explicitly passed None is not col.null
            # therefore we must handle it separately
            return cstruct

        # get the initial dictionary from our mapping base class
        r = super().deserialize(node, cstruct)
        if cstruct is col.null:
            return cstruct

        # next, iterate over available variants and return the first
        # matched structure.
        rv = None
        for variant in self.variants:
            try:
                rv = variant.deserialize(r)
                break
            except col.Invalid:
                continue
        else:
            raise col.Invalid(node, 'None of the variants matches provided data', cstruct)
        return rv

    def serialize(self, node, appstruct: NamedTuple):
        if appstruct is col.null:
            return super().serialize(node, appstruct)
        return super().serialize(
            node,
            {denormalize_name(k)[0]: v for k, v in appstruct._asdict().items()}
        )


class Int(col.Int):

    def serialize(self, node, appstruct):
        """ Default colander integer serializer returns a string representation
        of a number, whereas we want identical representation of the original data.
        """
        r = super().serialize(node, appstruct)
        if r is col.null:
            return r
        return int(r)