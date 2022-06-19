from enum import Enum
from typing import NamedTuple, Dict, Any, Sequence, Union, Tuple, Optional, Set, List, FrozenSet

import pytest

import typeit
from typeit import flags
from typeit import schema
from typeit.sums import Either


def test_type_with_unclarified_list():
    class X(NamedTuple):
        x: Sequence
        y: List

    mk_main, serialize_main = typeit.TypeConstructor ^ X
    x = mk_main({'x': [], 'y': []})
    x = mk_main({'x': [1], 'y': ['1']})
    assert x.x[0] == int(x.y[0])
    x = mk_main({'x': ['Hello'], 'y': ['World']})
    assert f'{x.x[0]} {x.y[0]}' == 'Hello World'


def test_primitives_strictness():
    class X(NamedTuple):
        a: int
        b: str
        c: float
        d: bool

    mk_x, serialize_x = typeit.TypeConstructor ^ X
    mk_x_nonstrict, serialize_x_nonstrict = typeit.TypeConstructor & flags.NonStrictPrimitives ^ X

    data = {
        'a': '1',
        'b': '2',
        'c': 5,
        'd': 1
    }

    data_X = X(
        a='1',
        b='2',
        c=5,
        d=1,
    )

    with pytest.raises(typeit.Error):
        mk_x(data)

    with pytest.raises(typeit.Error):
        serialize_x(data_X)

    assert mk_x_nonstrict(data) == X(
        a=1,
        b='2',
        c=5.0,
        d=True,
    )
    assert serialize_x_nonstrict(data_X) == dict(
        a=1,
        b='2',
        c=5.0,
        d=True
    )


def test_serialize_list():
    class X(NamedTuple):
        x: None | Sequence[str]

    mk_x, serialize_x = typeit.TypeConstructor ^ X
    data = {
        'x': ['str'],
    }
    x = mk_x(data)
    assert serialize_x(x) == data

    data = {
        'x': None,
    }
    x = mk_x(data)
    assert serialize_x(x) == data


def test_serialize_union_lists():
    """ This test makes sure that primitive values are matched strictly
    when it comes to serialization / deserialization
    """
    class X(NamedTuple):
        x: Sequence[str] | Sequence[float] | Sequence[int]

    mk_x, serialize_x = typeit.TypeConstructor ^ X
    data = {
        'x': [1],
    }
    x = mk_x(data)
    assert serialize_x(x) == data


def test_type_with_sequence():
    class X(NamedTuple):
        x: int
        y: Sequence[Any]
        z: Sequence[str]

    mk_main, serializer = typeit.TypeConstructor(X)

    x = mk_main({'x': 1, 'y': [], 'z': ['Hello']})
    assert x.y == []
    assert x.z[0] == 'Hello'


def test_type_with_tuple_primitives():
    # There are several forms of tuple declarations
    # https://docs.python.org/3/library/typing.html#typing.Tuple
    # We want to support all possible fixed-length tuples,
    # including empty one
    class X(NamedTuple):
        a: Tuple[str, int]  # fixed N-tuple
        b: Tuple            # the following are equivalent
        c: tuple

    mk_x, serializer = typeit.TypeConstructor(X)

    x = mk_x({
        'a': ['value', 5],
        'b': (),
        'c': [],
        'd': ['Hello', 'Random', 'Value', 5, None, True, {}],
    })
    assert x.a == ('value', 5)
    assert x.b == ()
    assert x.b == x.c

    with pytest.raises(typeit.Error):
        # 'abc' is not int
        x = mk_x({
            'a': ['value', 'abc'],
            'b': [],
            'c': [],
        })

    with pytest.raises(typeit.Error):
        # .c field is required
        x = mk_x({
            'a': ['value', 5],
            'b': [],
        })

    with pytest.raises(typeit.Error):
        # .c field is required to be fixed sequence
        x = mk_x({
            'a': ['value', 'abc'],
            'b': (),
            'c': None,
        })


def test_type_with_complex_tuples():
    class Y(NamedTuple):
        a: Dict

    class X(NamedTuple):
        a: Tuple[Tuple[Dict, Y], int]
        b: Optional[Any]

    mk_x, serializer = typeit.TypeConstructor(X)

    x = mk_x({
        'a': [
            [{}, {'a': {'inner': 'value'}}],
            5
        ],
    })
    assert isinstance(x.a[0][1], Y)
    assert isinstance(x.a[1], int)
    assert x.b is None

    x = mk_x({
        'a': [
            [{}, {'a': {'inner': 'value'}}],
            5
        ],
        'b': Y(a={})
    })
    assert isinstance(x.b, Y)


def test_unsupported_variable_length_tuples():
    class X(NamedTuple):
        a: Tuple[int, ...]

    with pytest.raises(TypeError):
        mk_x, serialize_x = typeit.TypeConstructor(X)


def test_enum_like_types():
    class Enums(Enum):
        A = 'a'
        B = 'b'

    class X(NamedTuple):
        e: Enums

    mk_x, serialize_x = typeit.TypeConstructor(X)

    data = {'e': 'a'}
    x = mk_x(data)
    assert isinstance(x.e, Enums)
    assert data == serialize_x(x)

    with pytest.raises(typeit.Error):
        x = mk_x({'e': None})


def test_sum_types_as_union():
    class Data(NamedTuple):
        value: str

    class MyEither(Either):
        class Left:
            err: str

        class Right:
            data: Data
            version: str
            name: str

    class X(NamedTuple):
        x: MyEither

    mk_x, serialize_x = typeit.TypeConstructor ^ X
    x_data = {
        'x': ('left', {'err': 'Error'})
    }
    x = mk_x(x_data)
    assert isinstance(x.x, Either)
    assert isinstance(x.x, MyEither)
    assert isinstance(x.x, MyEither.Left)
    assert isinstance(x.x, Either.Left)
    assert not isinstance(x.x, Either.Right)
    assert not isinstance(x.x, MyEither.Right)
    assert isinstance(x.x.err, str)
    assert x.x.err == 'Error'
    assert serialize_x(x) == x_data

    x_data = {
        'x': ('right', {
            'data': {'value': 'Value'},
            'version': '1',
            'name': 'Name',
        })
    }
    x = mk_x(x_data)
    assert isinstance(x.x, Either)
    assert isinstance(x.x, MyEither)
    assert isinstance(x.x, MyEither.Right)
    assert isinstance(x.x, Either.Right)
    assert not isinstance(x.x, Either.Left)
    assert not isinstance(x.x, MyEither.Left)
    assert isinstance(x.x.data, Data)
    assert isinstance(x.x.version, str)
    assert x.x.data == Data(value='Value')
    assert x.x.version == '1'
    assert x.x.name == 'Name'
    assert serialize_x(x) == x_data

    with pytest.raises(typeit.Error):
        # version is missing
        x = mk_x({
            'x': ('right', {
                'data': {'value': 'Value'},
                'name': 'Name',
            })
        })


def test_enum_unions_serialization():
    class E0(Enum):
        A = 'a'
        B = 'b'
        C = 'C'

    class E1(Enum):
        X = 'x'
        Y = 'y'
        Z = 'z'

    EType = E0 | E1

    class MyType(NamedTuple):
        val: EType

    __, serializer = typeit.TypeConstructor(MyType)

    assert serializer(MyType(val=E1.Z)) == {'val': 'z'}


def test_type_with_empty_enum_variant():
    class Types(Enum):
        A = ''
        B = 'b'

    class X(NamedTuple):
        x: int
        y: Types

    mk_x, serializer = typeit.TypeConstructor(X)

    for variant in Types:
        x = mk_x({'x': 1, 'y': variant.value})
        assert x.y is variant

    with pytest.raises(typeit.Error):
        x = mk_x({'x': 1, 'y': None})


def test_type_with_set():
    class X(NamedTuple):
        a: FrozenSet
        b: FrozenSet[Any]
        c: frozenset
        d: FrozenSet[int]
        e: set
        f: Set
        g: Set[Any]
        h: Set[int]

    mk_x, serializer = typeit.TypeConstructor(X)

    x = mk_x({
        'a': [],
        'b': [],
        'c': [],
        'd': [1],
        'e': [],
        'f': [],
        'g': [],
        'h': [1],
    })
    assert x.a == x.b == x.c == frozenset()
    assert isinstance(x.d, frozenset)
    assert isinstance(x.e, set)
    assert x.h == {1}
    assert x.d == x.h


def test_parse_sequence():
    class X(NamedTuple):
        x: int
        y: Dict[str, Any]

    XS = Sequence[X]

    data = [{'x': 1, 'y': {}}]
    mk_xs, serialize_xs = typeit.TypeConstructor(XS)
    z = mk_xs(data)
    assert z[0].x == 1
    assert serialize_xs(z) == data

    # Sequences with primitives
    XS = Sequence[int]

    data = [1, 2, 3]
    mk_xs, serialize_xs = typeit.TypeConstructor(XS)

    z = mk_xs(data)
    assert z[0] == 1
    assert serialize_xs(z) == data


@pytest.mark.parametrize('typ, data', (
    (int, 1),
    (bool, True),
    (str, '1'),
    (Dict[str, Any], {'x': 1, 'y': True, 'z': '1'})
))
def test_parse_builtins(typ, data):
    mk_x, serialize_x = typeit.TypeConstructor(typ)

    z = mk_x(data)
    assert z == data
    assert serialize_x(z) == data


def test_schema_node():
    x = schema.nodes.SchemaNode(schema.primitives.Int())
    assert x.__repr__().startswith('Int(strict)')


def test_type_with_dict():
    """ Create a type with an explicit dictionary value
    that can hold any kv pairs
    """
    class X(NamedTuple):
        x: int
        y: Dict[str, Any]

    mk_x, serializer = typeit.TypeConstructor(X)

    with pytest.raises(typeit.Error):
        mk_x({})

    with pytest.raises(typeit.Error):
        mk_x({'x': 1})

    x = mk_x({'x': 1, 'y': {'x': 1}})
    assert x.x == x.y['x']


def test_name_overrides():
    class X(NamedTuple):
        x: int

    data = {'my-x': 1}

    with pytest.raises(typeit.Error):
        mk_x, serialize_x = typeit.TypeConstructor ^ X
        mk_x(data)

    mk_x, serialize_x = typeit.TypeConstructor & {X.x: 'my-x'} ^ X
    x = mk_x(data)
    assert serialize_x(x) == data


@pytest.mark.parametrize('typ', [
    int,
    str,
    bool,
    float,
    None,
    Sequence,
])
def test_parse_builtins_and_sequences(typ):
    mk_x, serialize_x = typeit.TypeConstructor ^ typ


def test_default_namedtuple_values():
    class X(NamedTuple):
        x: int = 1

    data = {}

    mk_x, serialize_x = typeit.TypeConstructor ^ X

    x = mk_x(data)
    assert isinstance(x, X)
    assert x.x == 1
    assert serialize_x(x) == {'x': 1}


def test_default_init_based_value():
    class X:
        def __init__(self, x: int, y: int = 1):
            self.x = x
            self.y = y

    data = {'x': 0}

    mk_x, serialize_x = typeit.TypeConstructor ^ X

    x = mk_x(data)
    assert isinstance(x, X)
    assert x.x == 0 and x.y == 1
    assert serialize_x(x) == {'x': 0, 'y': 1}
