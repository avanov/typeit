from typing import NamedTuple

import pytest

from typeit import TypeConstructor, flags, Error


def test_bytes():
    class X(NamedTuple):
        x: bytes

    non_strict_mk_x, non_strict_dict_x = TypeConstructor & flags.NonStrictPrimitives ^ X
    strict_mk_x, strict_dict_x = TypeConstructor ^ X

    data = {'x': 'abc'}
    x = non_strict_mk_x(data)
    assert x.x == b'abc'

    with pytest.raises(Error):
        strict_mk_x(data)

    data_strict = {'x': b'abc'}
    x_non_strict = non_strict_mk_x(data_strict)
    x_strict = strict_mk_x(data_strict)
    assert x_non_strict == x_strict

    assert non_strict_dict_x(x_strict) == strict_dict_x(x_non_strict) == {'x': b'abc'}
