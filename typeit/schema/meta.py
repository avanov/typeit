from typing import Type, NamedTuple
from . import nodes


class TypeExtension(NamedTuple):
    typ: Type
    schema: nodes.SchemaNode

    def __lshift__(self, other) -> 'TypeExtension':
        self.schema.add(nodes.SchemaNode(other))
        return self


class SubscriptableSchemaTypeM(type):
    """ A metaclass for schemas that allow specifying types
    for which they are defined during type construction composition.

    The *M suffix in the name stands for "Meta" to indicate that
    this class should be used only as a metaclass.
    """
    def __getitem__(cls, item: Type) -> TypeExtension:
        return TypeExtension(
            typ=item,
            schema=nodes.SchemaNode(cls()),
        )

    def __repr__(self):
        return f'{self.__name__}'

    __str__ = __repr__
