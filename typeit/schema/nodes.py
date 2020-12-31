from typing import Iterable

from pyrsistent import pvector, pmap
import colander as col


Null = col.null


class SchemaNode(col.SchemaNode):
    """ Colander's SchemaNode doesn't show node type in it's repr,
    we fix it with this subclass.
    """
    children: Iterable

    def __repr__(self) -> str:
        return f'{self.typ}'


class TupleSchema(col.TupleSchema):
    pass


class SequenceSchema(col.SequenceSchema):
    pass


class SetSchema(SequenceSchema):
    def __init__(self, *args, frozen=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.frozen = frozen

    def deserialize(self, *args, **kwargs):
        r = super().deserialize(*args, **kwargs)
        if r in (Null, None):
            return r
        if self.frozen:
            return frozenset(r)
        return set(r)


class PVectorSchema(SequenceSchema):
    def deserialize(self, *args, **kwargs):
        r = super().deserialize(*args, **kwargs)
        if r in (Null, None):
            return r
        return pvector(r)


class PMapSchema(SchemaNode):
    def deserialize(self, *args, **kwargs):
        r = super().deserialize(*args, **kwargs)
        if r in (Null, None):
            return r
        return pmap(r)
