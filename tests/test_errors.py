from typing import NamedTuple

import typeit


class X(NamedTuple):
    x: int


def test_error():
    mk_x, _ = typeit.TypeConstructor ^ X
    try:
        mk_x({'x': '1'})
    except Exception as e:
        assert isinstance(e, typeit.Error)
        assert str(e).startswith('\n(1) x: ')
