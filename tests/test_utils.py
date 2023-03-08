import typeit
from typeit.schema.errors import InvalidData
from typeit import utils
from typing import NamedTuple, Sequence
from enum import Enum


def test_normalization():
    name = 'abc'
    normalized = utils.normalize_name(name)
    assert normalized == name

    name = 'def'
    normalized = utils.normalize_name(name)
    assert normalized == 'overridden__def'


def test_iter_invalid_data():
    class ItemType(Enum):
        ONE = 'one'
        TWO = 'two'

    class Item(NamedTuple):
        val: ItemType

    class X(NamedTuple):
        items: Sequence[Item]
        item: Item

    mk_x, serialize_x = typeit.TypeConstructor(X)

    data = {
        'items': [
            {'val': 'one'},
            {'val': 'two'},
            {'val': 'three'},
            {'val': 'four'},
        ]
    }

    try:
        x = mk_x(data)
    except typeit.Error as e:
        for inv in e:
            assert isinstance(inv, InvalidData)


def test_invalid_root_data():
    mk_int, serialize_int = typeit.TypeConstructor ^ int
    try:
        mk_int('1')
    except typeit.Error as e:
        x = list(e)  # this triggers root traversal


def test_iter_invalid_serialize():
    mk_int, serialize_int = typeit.TypeConstructor ^ int
    try:
        serialize_int('1')
    except typeit.Error as e:
        x = list(e)

    class X(NamedTuple):
        a: int
        b: bool

    mk_x, serialize_x = typeit.TypeConstructor ^ X

    data = {
        'a': 1,
        'b': True,
    }
    x = mk_x(data)
    x = x._replace(b=1)
    try:
        serialize_x(x)
    except typeit.Error as e:
        x = list(e)


def test_new_init():
    class X(NamedTuple):
        a: int
        b: bool

    a = 1
    b = True
    res = utils.new(X)
    assert res.a == a
    assert res.b == b

    res1 = utils.new(X, res)