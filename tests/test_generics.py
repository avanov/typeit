from dataclasses import dataclass
from typing import Generic, TypeVar, NamedTuple, Sequence
import json

from pvectorc import pvector

import typeit


A = TypeVar('A')

@dataclass(frozen=True, slots=True)
class Entity(Generic[A]):
    """ A generic representation of a database-stored entity.
    """
    pk: int
    entry: A


class InnerEntry(NamedTuple):
    entry_id: int
    entry_name: str


class Item(NamedTuple):
    item_id: int
    inner: InnerEntry


class PersistedItem(Entity[Item]):
    pass


class DatabaseResponse(NamedTuple):
    name: str
    items: Sequence[PersistedItem] = pvector()


def test_generic():

    mk_response, serialize_response = typeit.TypeConstructor ^ DatabaseResponse

    serialized = {
        "name": "response",
        "items": [
            {
                "pk": 1,
                "entry": {
                    "item_id": 1,
                    "inner": {
                        "entry_id": 2,
                        "entry_name": "entry_name",
                    }
                }
            }
        ]
    }
    x = serialize_response(mk_response(serialized))
    json.dumps(x)
    assert x == serialized
