from typing import NewType
import typeit


def test_newtype():
    Age = NewType('Age', int)
    mk_age, serialize_age = typeit.TypeConstructor ^ Age

    a = mk_age(1)
    assert a == 1
    assert isinstance(a, int)
    assert 1 == serialize_age(a)
