import collections
from typing import Mapping, Any, Union, Optional, Sequence
from typing import NamedTuple
from typing_extensions import Literal

import pytest
from typeit import type_constructor, Invalid


def test_mapping():
    class X(NamedTuple):
        x: Mapping
        y: Mapping[str, Any]
        z: collections.abc.Mapping

    mk_x, dict_x = type_constructor ^ X


def test_sequence():
    class X(NamedTuple):
        xs: collections.abc.Sequence

    mk_x, dict_x = type_constructor ^ X


def test_sets():
    class X(NamedTuple):
        xs: collections.abc.Set
        ys: collections.abc.MutableSet

    mk_x, dict_x = type_constructor ^ X


def test_literals():
    class X(NamedTuple):
        x: Literal[1]
        y: Literal[1, 'a']
        z: Literal[None, 1]

    mk_x, dict_x = type_constructor ^ X

    data = {
        'x': 1,
        'y': 'a',
        'z': None,
    }
    x = mk_x(data)
    assert x.x == 1
    assert x.y == 'a'
    assert x.z is None
    assert dict_x(x) == data

    data = {
        'x': 1,
        'y': 1,
        'z': 1
    }
    x = mk_x(data)
    assert x.y == 1
    assert x.z == 1

    for case in (
        {
            'x': '1',
            'y': 'a',
        },
        {
            'x': 2,
            'y': 'a',
        },
    ):
        with pytest.raises(Invalid):
            mk_x(case)

    x = X(None, None, 3)
    with pytest.raises(Invalid):
        dict_x(x)


def test_literals_included():
    class X(NamedTuple):
        x: Union[Literal[1], None]
        y: Optional[Literal[1]]
        z: Sequence[Literal[1]]

    mk_x, dict_x = type_constructor ^ X

    data = {
        'x': None,
        'y': None,
        'z': [1],
    }
    x = mk_x(data)
    assert x.z == [1]
    assert dict_x(x) == data

    mk_x({
        'x': None,
        'y': None,
        'z': [1, 1],
    })

    with pytest.raises(Invalid):
        mk_x({
            'x': None,
            'y': None,
            'z': [1, 2],
        })
