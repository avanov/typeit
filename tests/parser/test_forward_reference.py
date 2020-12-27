from typing import NamedTuple, Optional, Sequence, Any

from pyrsistent.typing import PVector

import typeit


class X(NamedTuple):
    x: int
    y: Optional['Y']
    z: Sequence['Y']


class Y(NamedTuple):
    y: int
    x: X


class Tree(NamedTuple):
    left: Optional['Tree']
    right: Optional['Tree']
    value: Any


def test_forward_ref_struct():
    mk_x, serialize_x = typeit.TypeConstructor ^ X
    mk_y, serialize_y = typeit.TypeConstructor ^ Y

    data = dict(
        x=1,
        y=dict(
            y=1,
            x=dict(
                x=2,
                y=None,
                z=[]
            )
        ),
        z=[
            dict(
                y=1,
                x=dict(
                    x=2,
                    y=None,
                    z=[]
                )
            )
        ]
    )
    x = mk_x(data)
    assert isinstance(x, X)
    assert isinstance(x.y, Y)
    assert isinstance(x.y.x, X)
    assert x.y.y == 1
    assert isinstance(x.z[0], Y)
    assert x.z[0] == x.y
    assert x.y.x.y is None
    assert data == serialize_x(x)


def test_recursive_ref():
    mk_tree, serialize_tree = typeit.TypeConstructor ^ Tree
    tree = mk_tree(
        dict(
            left=dict(
                left=None,
                right=None,
                value=1
            ),
            right=None,
            value=0
        )
    )
    assert isinstance(tree, Tree)
    assert isinstance(tree.left, Tree)
    assert tree.right is None
    assert tree.left.left is None
    assert tree.left.right is None
    assert tree.value == 0
    assert tree.left.value == 1

