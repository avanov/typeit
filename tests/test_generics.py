from dataclasses import dataclass
from typing import Generic, TypeVar, NamedTuple, Sequence

import typeit


A = TypeVar('A')

@dataclass(frozen=True, slots=True)
class X(Generic[A]):
    pk: int
    entry: A


def test_generic():
    class Item(NamedTuple):
        value: str

    class Concrete(X[Item]):
        pass

    class Wrapper(NamedTuple):
        vals: Sequence[Concrete]

    mk_wrapper, serialize_wrapper = typeit.TypeConstructor ^ Wrapper

    serialized = {
        "vals": [
            {
                "pk": 1,
                "entry": {
                    "value": "item value"
                }
            }
        ]
    }
    assert serialize_wrapper(mk_wrapper(serialized)) == serialized
