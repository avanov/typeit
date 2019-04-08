from typing import Union

import colander as col


def _strict_deserialize(node, rval, cstruct):
    if rval in (col.null, None):
        return rval
    if type(rval) is not type(cstruct):
        raise col.Invalid(
            node,
            'Primitive values should adhere strict type semantics',
            cstruct
        )
    return rval


def _strict_serialize(node, allowed_type, appstruct):
    if appstruct in (col.null, None):
        return appstruct

    if type(appstruct) is not allowed_type:
        raise col.Invalid(
            node,
            'Primitive values should adhere strict type semantics',
            appstruct
        )
    return appstruct


class AcceptEverything(col.SchemaType):
    """ A schema type to correspond to typing.Any, i.e. allows
    any data to pass through the type constructor.
    """
    def serialize(self, node, appstruct):
        return appstruct

    def deserialize(self, node, cstruct):
        return cstruct


class NonStrictInt(col.Int):

    def serialize(self, node, appstruct):
        """ Default colander integer serializer returns a string representation
        of a number, whereas we want identical representation of the original data.
        """
        r = super().serialize(node, appstruct)
        if r in (col.null, 'None'):
            return None
        return int(r)


class Int(NonStrictInt):

    def deserialize(self, node, cstruct):
        r = super().deserialize(node, cstruct)
        return _strict_deserialize(node, r, cstruct)

    def serialize(self, node, appstruct):
        """ Default colander integer serializer returns a string representation
        of a number, whereas we want identical representation of the original data.
        """
        appstruct = _strict_serialize(node, int, appstruct)
        return super().serialize(node, appstruct)


class NonStrictBool(col.Bool):

    def serialize(self, node, appstruct):
        """ Default colander bool serializer returns a string representation
        of a boolean flag, whereas we want identical representation of the original data.
        """
        r = super().serialize(node, appstruct)
        if r in (col.null, 'None'):
            return None
        return {'false': False, 'true': True}[r]


class Bool(NonStrictBool):

    def deserialize(self, node, cstruct):
        r = super().deserialize(node, cstruct)
        return _strict_deserialize(node, r, cstruct)

    def serialize(self, node, appstruct):
        """ Default colander bool serializer returns a string representation
        of a boolean flag, whereas we want identical representation of the original data.
        """
        appstruct = _strict_serialize(node, bool, appstruct)
        return super().serialize(node, appstruct)


class NonStrictStr(col.Str):

    def serialize(self, node, appstruct):
        """ Default colander str serializer serializes None as 'None',
        whereas we want identical representation of the original data,
        with strict primitive type semantics
        """
        r = super().serialize(node, appstruct)
        if r in (col.null, 'None'):
            return None
        return r


class Str(NonStrictStr):

    def deserialize(self, node, cstruct):
        r = super().deserialize(node, cstruct)
        return _strict_deserialize(node, r, cstruct)

    def serialize(self, node, appstruct):
        """ Default colander str serializer serializes None as 'None',
        whereas we want identical representation of the original data,
        with strict primitive type semantics
        """
        appstruct = _strict_serialize(node, str, appstruct)
        return super().serialize(node, appstruct)


class NonStrictFloat(col.Float):

    def serialize(self, node, appstruct):
        r = super().serialize(node, appstruct)
        if r in (col.null, 'None'):
            return None
        return float(r)


class Float(NonStrictFloat):

    def deserialize(self, node, cstruct):
        r = super().deserialize(node, cstruct)
        return _strict_deserialize(node, r, cstruct)

    def serialize(self, node, appstruct):
        appstruct = _strict_serialize(node, float, appstruct)
        return super().serialize(node, appstruct)


NonStrictPrimitiveSchemaTypeT = Union[
    AcceptEverything,
    NonStrictStr,
    NonStrictInt,
    NonStrictFloat,
    NonStrictBool,
]


PrimitiveSchemaTypeT = Union[
    AcceptEverything,
    Str,
    Int,
    Float,
    Bool,
]
