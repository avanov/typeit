from typing import NamedTuple, Union, Mapping, Any, Dict

import colander
import pytest

from typeit import type_constructor, parser as p, flags
from typeit.compat import PY36


def test_type_with_unions():
    class VariantA(NamedTuple):
        variant_a: int

    class VariantB(NamedTuple):
        variant_b: int
        variant_b_attr: int

    class X(NamedTuple):
        x: Union[None, VariantA, VariantB]
        y: Union[str, VariantA]

    mk_x, dict_x = p.type_constructor(X)

    x = mk_x({'x': {'variant_a': 1}, 'y': 'y'})
    assert isinstance(x.x, VariantA)

    data = {'x': {'variant_b': 1, 'variant_b_attr': 1}, 'y': 'y'}
    x = mk_x(data)
    assert isinstance(x.x, VariantB)

    assert data == dict_x(x)

    assert mk_x({'x': None, 'y': 'y'}) == mk_x({'y': 'y'})
    with pytest.raises(colander.Invalid):
        # this is not the same as mk_x({}),
        # the empty structure is passed as attribute x,
        # which should match with only an empty named tuple definition,
        # which is not the same as None.
        mk_x({'x': {}})


def test_type_with_primitive_union():
    class X(NamedTuple):
        x: Union[None, str]

    mk_x, dict_x = type_constructor(X)

    x = mk_x({'x': None})
    assert x.x is None

    data = {'x': 'test'}
    x = mk_x(data)
    assert x.x == 'test'

    assert data == dict_x(x)


def test_union_primitive_match():
    class X(NamedTuple):
        # here, str() accepts everything that could be passed to int(),
        # and int() accepts everything that could be passed to float(),
        # and we still want to get int values instead of string values,
        # and float values instead of rounded int values.
        x: Union[str, int, float, bool]

    mk_x, serializer = type_constructor(X)

    x = mk_x({'x': 1})
    assert isinstance(x.x, int)

    x = mk_x({'x': 1.0})
    assert isinstance(x.x, float)

    if not PY36:
        # Python 3.6 has a bug that drops bool types from
        # unions that include int already, so
        # x: Union[int, bool] -- will be reduced to just `x: int`
        # x: Union[str, bool] -- will be left as is
        x = mk_x({'x': True})
        assert isinstance(x.x, bool)

    data = {'x': '1'}
    x = mk_x(data)
    assert isinstance(x.x, str)
    assert serializer(x) == data


def test_test_union_primitive_and_compound_types():
    class X(NamedTuple):
        x: Union[str, Dict[str, Any]]

    mk_x, dict_x = type_constructor(X)
    mk_x_nonstrict, dict_x_nonstrict = type_constructor(X, overrides={flags.NON_STRICT_PRIMITIVES: 1})

    data = {'x': {'key': 'value'}}
    x = mk_x(data)
    assert dict_x(x) == data

    x = mk_x_nonstrict(data)
    assert dict_x_nonstrict(x) == data