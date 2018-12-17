import pytest
import pickle
from typing import NamedTuple
from typeit.sums import SumType, Variant


# These types are defined outside test cases
# because pickle requires classes to be defined in a module scope.
class X(SumType):
    VARIANT_A: Variant[str] = 'variant_a'


class Y(SumType):
    VARIANT_A: Variant[str] = 'variant_a'


def test_enum_like_api():
    """ SumType should support the same usage patterns as Enum.
    """
    assert X.VARIANT_A != Y.VARIANT_A
    assert X.VARIANT_A is not Y.VARIANT_A

    with pytest.raises(ValueError):
        X(Y.VARIANT_A)

    assert X('variant_a') is X.VARIANT_A

    assert X.VARIANT_A in X

    assert [X.VARIANT_A] == [x for x in X]

    assert X(X.VARIANT_A) is X.VARIANT_A

    assert type(X.VARIANT_A) is X

    assert isinstance(X.VARIANT_A, X)

    assert X(pickle.loads(pickle.dumps(X.VARIANT_A))) is X.VARIANT_A


class Z(SumType):
    A: Variant[str]

    class _BData(NamedTuple):
        x: str
        y: int
        z: float

    B: Variant[_BData]
    C: Variant[None]


def test_sum_variants():
    x = Z.A('111')
    y = Z.B(x='1', y=2, z=3.0)
    c = Z.C()

    assert type(x) is Z
    assert type(x) is type(y)
    assert isinstance(x, Z)
    assert isinstance(y, Z)

    assert x.value == 'a'
    assert x.data == '111'

    assert y.data.x == '1'
    assert y.data.y == 2
    assert isinstance(y.data.z, float)
    assert isinstance(y.data, Z._BData)

    assert c.data is None
