from typeit import utils
from typing import NamedTuple, Sequence
from typeit import type_constructor
from enum import Enum
import colander


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

    mk_x, dict_x = type_constructor(X)

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
    except colander.Invalid as e:
        for inv in utils.iter_invalid_data(e, data):
            assert isinstance(inv, utils.InvalidData)
