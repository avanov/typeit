import collections
from typing import Mapping, Any
from typing import NamedTuple

from typeit import type_constructor


def test_mapping():
    class X(NamedTuple):
        x: Mapping
        y: Mapping[str, Any]
        z: collections.abc.Mapping

    mk_x, dict_x = type_constructor(X)


def test_sequence():
    class X(NamedTuple):
        xs: collections.abc.Sequence

    mk_x, dict_x = type_constructor(X)


def test_sets():
    class X(NamedTuple):
        xs: collections.abc.Set
        ys: collections.abc.MutableSet

    mk_x, dict_x = type_constructor(X)
