from typing import Type, NamedTuple, Tuple as PyTuple, Any

import colander as col
from pyrsistent import pvector
from pyrsistent.typing import PVector

from . import nodes
from ..combinator.combinator import Combinator


class TypeExtension(NamedTuple):
    typ: Type
    schema: PyTuple[Type['SchemaType'], PVector[Any]]

    def __and__(self, other) -> Combinator:
        return Combinator() & self & other

    def __add__(self, other) -> 'TypeExtension':
        return self._replace(
            schema=(self.schema[0], self.schema[1].append(nodes.SchemaNode(other)))
        )


class SubscriptableSchemaTypeM(type):
    """ A metaclass for schemas that allow specifying types
    for which they are defined during type construction composition.

    The *M suffix in the name stands for "Meta" to indicate that
    this class should be used only as a metaclass.
    """
    def __getitem__(cls: Type['SchemaType'], item: Type) -> TypeExtension:
        # ``cls`` is a schema type here
        return TypeExtension(
            typ=item,
            schema=(cls, pvector()),
        )

    def __repr__(self) -> str:
        return f'{self.__name__}'

    __str__ = __repr__


class SchemaType(col.SchemaType, metaclass=SubscriptableSchemaTypeM):
    pass


class Int(col.Int, metaclass=SubscriptableSchemaTypeM):
    pass


class Bool(col.Bool, metaclass=SubscriptableSchemaTypeM):
    pass


class Str(col.Str, metaclass=SubscriptableSchemaTypeM):
    pass


class Float(col.Float, metaclass=SubscriptableSchemaTypeM):
    pass


class Tuple(col.Tuple, metaclass=SubscriptableSchemaTypeM):
    pass


class Mapping(col.Mapping, metaclass=SubscriptableSchemaTypeM):
    pass
