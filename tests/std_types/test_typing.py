import collections
from enum import Enum
from typing import Mapping, Any, Union, Optional, Sequence, Dict
from typing import NamedTuple

from pyrsistent.typing import PMap

from typeit.compat import Literal

import pytest
from typeit import TypeConstructor, Error


def test_mapping():
    class X(NamedTuple):
        x: Mapping[Any, Any]
        y: Dict[str, Any]
        z: collections.abc.Mapping

    mk_x, serialize_x = TypeConstructor ^ X
    sub = {'a': 1, 'b': '2'}
    x = mk_x({'x': sub, 'y': sub, 'z': sub})
    assert x.x['a'] == 1
    assert x.x['b'] == '2'
    assert x.y['a'] == 1
    assert x.y['b'] == '2'
    assert x.z['a'] == 1
    assert x.z['b'] == '2'


def test_typed_mapping():
    class Attr(Enum):
        x = 'x'

    class X(NamedTuple):
        map_: Mapping[Attr, str]
        dict_: Dict[Attr, str]
        pmap_: PMap[Attr, str]

    mk_x, serialize_x = TypeConstructor ^ X

    x = mk_x({
        'map_': {'x': 'value'},
        'dict_': {'x': 'value'},
        'pmap_': {'x': 'value'}
    })
    assert x.map_[Attr.x] == 'value'
    assert x.dict_[Attr.x] == 'value'
    assert x.pmap_[Attr.x] == 'value'


def test_sequence():
    class X(NamedTuple):
        xs: collections.abc.Sequence

    mk_x, serialize_x = TypeConstructor ^ X


def test_sets():
    class X(NamedTuple):
        xs: collections.abc.Set
        ys: collections.abc.MutableSet

    mk_x, serialize_x = TypeConstructor ^ X


def test_literals():
    class X(NamedTuple):
        x: Literal[1]
        y: Literal[1, 'a']
        z: Literal[None, 1]

    mk_x, serialize_x = TypeConstructor ^ X

    data = {
        'x': 1,
        'y': 'a',
        'z': None,
    }
    x = mk_x(data)
    assert x.x == 1
    assert x.y == 'a'
    assert x.z is None
    assert serialize_x(x) == data

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
        with pytest.raises(Error):
            mk_x(case)

    x = X(None, None, 3)
    with pytest.raises(Error):
        serialize_x(x)


def test_literals_included():
    class X(NamedTuple):
        x: Union[Literal[1], None]
        y: Optional[Literal[1]]
        z: Sequence[Literal[1]]

    mk_x, serialize_x = TypeConstructor ^ X

    data = {
        'x': None,
        'y': None,
        'z': [1],
    }
    x = mk_x(data)
    assert x.z == [1]
    assert serialize_x(x) == data

    mk_x({
        'x': None,
        'y': None,
        'z': [1, 1],
    })

    with pytest.raises(Error):
        mk_x({
            'x': None,
            'y': None,
            'z': [1, 2],
        })
