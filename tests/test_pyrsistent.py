from typing import NamedTuple, Any, Optional

import pytest

import typeit as ty
import pyrsistent as ps


def test_pyrsistent_types():
    class X(NamedTuple):
        a: ps.typing.PMap[str, Any]
        b: ps.typing.PVector[ps.typing.PMap]
        c: Optional[ps.typing.PMap]

    mk_x, serialize_x = ty.TypeConstructor ^ X

    data = {
        'a': {'x': 'x', 'y': 'y'},
        'b': [{'x': 'x', 'y': 'y'}],
        'c': None
    }
    x = mk_x(data)
    assert isinstance(x.a, ps.PMap)
    assert isinstance(x.b, ps.PVector)
    assert isinstance(x.b[0], ps.PMap)
    assert serialize_x(x) == data

    data = {
        'a': None,
        'b': [{'x': 'x', 'y': 'y'}],
        'c': {'x': 'x', 'y': 'y'}
    }
    with pytest.raises(ty.Error):
        mk_x(data)
