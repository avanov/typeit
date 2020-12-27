from typing import NamedTuple, Union, Any, Dict, Optional, Mapping

import pytest

import typeit
from typeit import TypeConstructor, flags, Error


def test_type_with_unions():
    class VariantA(NamedTuple):
        variant_a: int

    class VariantB(NamedTuple):
        variant_b: int
        variant_b_attr: int

    class X(NamedTuple):
        x: Union[None, VariantA, VariantB]
        y: Union[str, VariantA]

    mk_x, serialize_x = typeit.TypeConstructor(X)

    x = mk_x({'x': {'variant_a': 1}, 'y': 'y'})
    assert isinstance(x.x, VariantA)

    data = {'x': {'variant_b': 1, 'variant_b_attr': 1}, 'y': 'y'}
    x = mk_x(data)
    assert isinstance(x.x, VariantB)

    assert data == serialize_x(x)

    assert mk_x({'x': None, 'y': 'y'}) == mk_x({'y': 'y'})
    with pytest.raises(typeit.Error):
        # this is not the same as mk_x({}),
        # the empty structure is passed as attribute x,
        # which should match with only an empty named tuple definition,
        # which is not the same as None.
        mk_x({'x': {}})


def test_type_with_primitive_union():
    class X(NamedTuple):
        x: Union[None, str]

    mk_x, serialize_x = TypeConstructor(X)

    x = mk_x({'x': None})
    assert x.x is None

    data = {'x': 'test'}
    x = mk_x(data)
    assert x.x == 'test'

    assert data == serialize_x(x)


def test_union_primitive_match():
    class X(NamedTuple):
        # here, str() accepts everything that could be passed to int(),
        # and int() accepts everything that could be passed to float(),
        # and we still want to get int values instead of string values,
        # and float values instead of rounded int values.
        x: Union[str, int, float, bool]

    mk_x, serializer = TypeConstructor(X)

    x = mk_x({'x': 1})
    assert isinstance(x.x, int)

    x = mk_x({'x': 1.0})
    assert isinstance(x.x, float)

    x = mk_x({'x': True})
    assert isinstance(x.x, bool)

    data = {'x': '1'}
    x = mk_x(data)
    assert isinstance(x.x, str)
    assert serializer(x) == data


def test_test_union_primitive_and_compound_types():
    class X(NamedTuple):
        x: Union[str, Dict[str, Any]]

    mk_x, serialize_x = TypeConstructor(X)
    mk_x_nonstrict, serialize_x_nonstrict = TypeConstructor & flags.NonStrictPrimitives ^ X

    data = {'x': {'key': 'value'}}
    x = mk_x(data)
    assert serialize_x(x) == data

    x = mk_x_nonstrict(data)
    assert serialize_x_nonstrict(x) == data


def test_union_mappings():
    class X(NamedTuple):
        x: Optional[Mapping[Any, Any]] = None

    mk_x, serialize_x = typeit.TypeConstructor ^ X
    serialize_x(mk_x({'x': None}))
    serialize_x(mk_x({'x': {'y': None}}))


def test_union_errors():
    class X(NamedTuple):
        x: Optional[int]

    mk_x, serialize_x = typeit.TypeConstructor ^ X

    with pytest.raises(Error):
        mk_x({'x': '1'})
    with pytest.raises(Error):
        serialize_x(X(x="5"))
