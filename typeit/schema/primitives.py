import typing as t

import colander as col
from .meta import SubscriptableSchemaTypeM
from .errors import Invalid


Null = col.null


def _strict_deserialize(node, allowed_type: t.Type, cstruct):
    if cstruct in (Null, None):
        return cstruct
    if type(cstruct) is not allowed_type:
        raise Invalid(
            node,
            f'Primitive values should adhere strict type semantics: '
            f'{type(cstruct)} was passed, {allowed_type} is expected by deserializer.',
            cstruct
        )
    return cstruct


def _strict_serialize(node, allowed_type: t.Type, appstruct):
    if appstruct in (Null, None):
        return appstruct

    if type(appstruct) is not allowed_type:
        raise Invalid(
            node,
            f'Primitive values should adhere strict type semantics: '
            f'{type(appstruct)} was passed, {allowed_type} is expected by serializer.',
            appstruct
        )
    return appstruct


class AcceptEverything(col.SchemaType, metaclass=SubscriptableSchemaTypeM):
    """ A schema type to correspond to typing.Any, i.e. allows
    any data to pass through the type constructor.
    """
    def serialize(self, node, appstruct):
        return appstruct

    def deserialize(self, node, cstruct):
        return cstruct


class NonStrictInt(col.Int, metaclass=SubscriptableSchemaTypeM):

    def serialize(self, node, appstruct):
        """ Default colander integer serializer returns a string representation
        of a number, whereas we want identical representation of the original data.
        """
        r = super().serialize(node, appstruct)
        if r in (Null, 'None'):
            return None
        return int(r)


class Int(NonStrictInt):

    def deserialize(self, node, cstruct):
        cstruct = _strict_deserialize(node, int, cstruct)
        return super().deserialize(node, cstruct)

    def serialize(self, node, appstruct):
        """ Default colander integer serializer returns a string representation
        of a number, whereas we want identical representation of the original data.
        """
        appstruct = _strict_serialize(node, int, appstruct)
        return super().serialize(node, appstruct)


class NonStrictBool(col.Bool, metaclass=SubscriptableSchemaTypeM):

    def serialize(self, node, appstruct):
        """ Default colander bool serializer returns a string representation
        of a boolean flag, whereas we want identical representation of the original data.
        """
        r = super().serialize(node, appstruct)
        if r in (Null, 'None'):
            return None
        return {'false': False, 'true': True}[r]


class Bool(NonStrictBool):

    def deserialize(self, node, cstruct):
        cstruct = _strict_deserialize(node, bool, cstruct)
        return super().deserialize(node, cstruct)

    def serialize(self, node, appstruct):
        """ Default colander bool serializer returns a string representation
        of a boolean flag, whereas we want identical representation of the original data.
        """
        appstruct = _strict_serialize(node, bool, appstruct)
        return super().serialize(node, appstruct)


class NonStrictStr(col.Str, metaclass=SubscriptableSchemaTypeM):

    def serialize(self, node, appstruct):
        """ Default colander str serializer serializes None as 'None',
        whereas we want identical representation of the original data,
        with strict primitive type semantics
        """
        r = super().serialize(node, appstruct)
        if r in (Null, 'None'):
            return None
        return r


class Str(NonStrictStr):

    def deserialize(self, node, cstruct):
        cstruct = _strict_deserialize(node, str, cstruct)
        return super().deserialize(node, cstruct)

    def serialize(self, node, appstruct):
        """ Default colander str serializer serializes None as 'None',
        whereas we want identical representation of the original data,
        with strict primitive type semantics
        """
        appstruct = _strict_serialize(node, str, appstruct)
        return super().serialize(node, appstruct)


class NonStrictFloat(col.Float, metaclass=SubscriptableSchemaTypeM):

    def serialize(self, node, appstruct):
        r = super().serialize(node, appstruct)
        if r in (Null, 'None'):
            return None
        return float(r)


class Float(NonStrictFloat):

    def deserialize(self, node, cstruct):
        cstruct = _strict_deserialize(node, float, cstruct)
        return super().deserialize(node, cstruct)

    def serialize(self, node, appstruct):
        appstruct = _strict_serialize(node, float, appstruct)
        return super().serialize(node, appstruct)


NonStrictPrimitiveSchemaTypeT = t.Union[
    AcceptEverything,
    NonStrictStr,
    NonStrictInt,
    NonStrictFloat,
    NonStrictBool,
]


PrimitiveSchemaTypeT = t.Union[
    AcceptEverything,
    Str,
    Int,
    Float,
    Bool,
]


# Maps primitive types that appear in type signatures
# to colander SchemaNodes responsible for serialization/deserialization
BUILTIN_TO_SCHEMA_TYPE: t.Mapping[t.Type, PrimitiveSchemaTypeT] = {
    t.Any: AcceptEverything(),
    str: Str(allow_empty=True),
    int: Int(),
    float: Float(),
    bool: Bool(),
}


NON_STRICT_BUILTIN_TO_SCHEMA_TYPE: t.Mapping[t.Type, NonStrictPrimitiveSchemaTypeT] = {
    t.Any: AcceptEverything(),
    str: NonStrictStr(allow_empty=True),
    int: NonStrictInt(),
    float: NonStrictFloat(),
    bool: NonStrictBool(),
}
