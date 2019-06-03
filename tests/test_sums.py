import pytest
import pickle
from typeit.sums import SumType


# These types are defined outside test cases
# because pickle requires classes to be defined in a module scope.
class X(SumType):
    class VARIANT_A(str): ...


def test_enum_like_api():
    """ SumType should support the same usage patterns as Enum.
    """
    class Y(SumType):
        class VARIANT_A(str): ...

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


def test_sum_variant_data_is_typed():
    class X(SumType):
        class VARIANT_A(str): ...

        class VARIANT_B(str): ...

    assert X.VARIANT_A is not X
    a_inst = X.VARIANT_A('111')
    assert isinstance(a_inst, X)
    assert isinstance(a_inst, X.VARIANT_A)
    assert not isinstance(a_inst, X.VARIANT_B)


def test_sum_variants():
    class Z(SumType):
        class A(str): ...

        class B:
            x: str
            y: int
            z: float

        class C: ...

    x = Z.A('111')
    y = Z.B(x='1', y=2, z=3.0)
    c = Z.C()

    assert type(x) is Z
    assert type(x) is type(y)
    assert isinstance(x, Z)
    assert isinstance(y, Z)

    assert y.x == '1'
    assert y.y == 2
    assert isinstance(y.z, float)

    assert c.data is None


def test_sum_variant_subclass_positional():
    class X(SumType):
        class A(str): ...

    x = X.A(5)
    assert type(x) is X
    assert isinstance(x, X)
